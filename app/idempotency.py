"""
Idempotency keys: make retrying a write safe.

A client sends `Idempotency-Key: <any unique string>` on a write request.
  - First time we see (user, key): run the request normally and remember the
    successful response.
  - Same key + same request again: return the remembered response and do NOT
    run the action a second time ("Idempotent-Replay: true" header).
  - Same key + a DIFFERENT request: refuse with 422 (the key is being misused).
  - Same key while the first request is still running: 409.

Rules worth knowing:
  - Keys are scoped per user, so two users can't collide.
  - Only successful (2xx) results are remembered. A failed attempt (e.g. 409
    "plan not approved yet") leaves no trace, so the client can retry later
    with the same key.
  - Keys expire after 24 hours; a claim stuck "in progress" (server crashed)
    is released after 60 seconds.
"""

import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.auth.jwt_handler import decode_access_token
from app.db import get_conn

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
KEY_TTL = timedelta(hours=24)
CLAIM_TTL = timedelta(seconds=60)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def fingerprint(method: str, path_and_query: str, plan_id: str | None, body: bytes) -> str:
    h = hashlib.sha256()
    for part in (method, path_and_query, plan_id or ""):
        h.update(part.encode() + b"\n")
    h.update(body)
    return h.hexdigest()


def begin(actor: str, key: str, fp: str):
    """Returns ("new" | "replay" | "mismatch" | "in_progress", row_or_None)."""
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM idempotency_keys WHERE created_at < ? "
            "OR (status_code IS NULL AND created_at < ?)",
            ((_now() - KEY_TTL).isoformat(), (_now() - CLAIM_TTL).isoformat()),
        )
        try:
            conn.execute(
                "INSERT INTO idempotency_keys (actor, key, fingerprint, created_at) VALUES (?,?,?,?)",
                (actor, key, fp, _now().isoformat()),
            )
            return "new", None
        except sqlite3.IntegrityError:  # someone already claimed this key
            row = conn.execute(
                "SELECT * FROM idempotency_keys WHERE actor = ? AND key = ?", (actor, key)
            ).fetchone()
    if row["fingerprint"] != fp:
        return "mismatch", None
    if row["status_code"] is None:
        return "in_progress", None
    return "replay", dict(row)


def complete(actor: str, key: str, status_code: int, body: bytes, content_type: str | None):
    with get_conn() as conn:
        conn.execute(
            "UPDATE idempotency_keys SET status_code = ?, response_body = ?, content_type = ? "
            "WHERE actor = ? AND key = ?",
            (status_code, body, content_type, actor, key),
        )


def abandon(actor: str, key: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM idempotency_keys WHERE actor = ? AND key = ?", (actor, key))


def _actor(request) -> str | None:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    payload = decode_access_token(auth[7:])
    return payload["sub"] if payload else None


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        key = request.headers.get("idempotency-key")
        actor = _actor(request)
        if key is None or actor is None or request.method not in WRITE_METHODS:
            return await call_next(request)  # nothing to do (no key / not logged in / not a write)

        path_and_query = request.url.path + ("?" + request.url.query if request.url.query else "")
        fp = fingerprint(request.method, path_and_query, request.headers.get("x-plan-id"),
                         await request.body())

        state, row = begin(actor, key, fp)
        if state == "replay":
            return Response(
                content=row["response_body"], status_code=row["status_code"],
                media_type=row["content_type"], headers={"Idempotent-Replay": "true"},
            )
        if state == "mismatch":
            return JSONResponse({"detail": "Idempotency-Key was already used with a different request"}, 422)
        if state == "in_progress":
            return JSONResponse({"detail": "A request with this Idempotency-Key is still being processed"}, 409)

        try:
            response = await call_next(request)
            body = b"".join([chunk async for chunk in response.body_iterator])
        except Exception:
            abandon(actor, key)
            raise

        if 200 <= response.status_code < 300:
            complete(actor, key, response.status_code, body, response.media_type)
        else:
            abandon(actor, key)  # failures are not remembered, so the client may retry
        return Response(content=body, status_code=response.status_code,
                        headers=dict(response.headers), media_type=response.media_type)
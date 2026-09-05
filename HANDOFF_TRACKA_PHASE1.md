\# Handoff — Track A, Phase 1



\*\*From:\*\* Track A

\*\*Status:\*\* Complete, tested manually

\*\*Commit:\*\* f3e3142



\## What's live



A FastAPI mock API implementing all 13 endpoints from `docs/PHASE0\_CONTRACT.md`,

with OAuth2/JWT auth and endpoint-level RBAC enforcement.



Run it with:

```powershell

uvicorn app.main:app --reload

```

Interactive docs at `http://127.0.0.1:8000/docs`.



\## Auth



`POST /auth/login` — OAuth2 password grant (form fields: `username`, `password`).

Returns `{"access\_token": "...", "token\_type": "bearer"}`.



Mock users (all password `password123`):

| Username | Role |

|---|---|

| alice\_viewer | viewer |

| bob\_agent | agent |

| carol\_approver | approver |

| dave\_admin | admin |



Pass the token as `Authorization: Bearer <token>` on every subsequent request.

Tokens expire after 30 minutes (`ACCESS\_TOKEN\_EXPIRE\_MINUTES` in `app/auth/jwt\_handler.py`).



\## RBAC behavior



Every route is guarded by `Depends(require\_risk\_tier(RiskTier.<tier>))` (see

`app/auth/rbac.py`). This checks the token's `role` claim against

`ROLE\_ALLOWED\_TIERS`, independent of anything a planner claims about its

own action's risk tier.



\- Missing/invalid/expired token → `401 Unauthorized`

\- Valid token, role not permitted for that endpoint's risk tier → `403 Forbidden`,

&#x20; body: `{"detail": "Role '<role>' is not permitted to perform '<tier>' actions"}`



\*\*Known contract ambiguity (unresolved):\*\* `PHASE0\_CONTRACT.md`'s roles table lists

`agent` as `read\_only, low\_risk\_write` only, but the note beneath it says agent

can \*request\* `high\_risk\_write` but not self-approve. I built RBAC assuming the

note is correct (agent allowed to request high\_risk\_write). If that's wrong,

`ROLE\_ALLOWED\_TIERS` in `app/auth/rbac.py` is the one place to change.



\## Endpoints



All 13 contract endpoints are live, grouped under `/customers`, `/subscriptions`,

`/invoices`, `/teams`, `/tickets`. Full list with request/response shapes is in

`/docs` (Swagger) once the server is running — not duplicated here to avoid

drift between this doc and the actual code.



\## Data layer



Everything is in-memory (plain Python dicts inside each route module) — resets

on every server restart. No persistence yet. This is fine for Phase 1; if

Track B's testing needs data to survive restarts, flag it and we'll figure out

whether that's a Phase 1 fix or deferred to a later phase.



\## What Track B needs to know



\- Base URL: `http://127.0.0.1:8000` (local dev only, no deployment yet)

\- Get a token via `/auth/login` before calling anything else

\- A plan's `risk\_tier` field (from `contracts/plan.py`) should match what

&#x20; the target endpoint actually enforces — if your planner assigns a

&#x20; `read\_only` tier to something that's actually `high\_risk\_write`, the

&#x20; API will reject it with 403 regardless, so this is a safety net, not a

&#x20; planning validation step Track B can skip.



\## Not yet built (later phases per README)

Approval workflow, audit logging, idempotency, rollback, observability.


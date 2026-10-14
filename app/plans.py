"""Storage for submitted plans (the approval queue lives in this table)."""

import json
from datetime import datetime, timezone

from contracts.plan import Plan

from app.db import get_conn


def save_plan(plan: Plan) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO plans (plan_id, endpoint, method, parameters, reason, "
            "expected_result, risk_tier, requires_approval, requested_by, status, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                plan.plan_id,
                plan.endpoint,
                plan.method,
                json.dumps(plan.parameters),
                plan.reason,
                plan.expected_result,
                plan.risk_tier.value,
                int(plan.requires_approval),
                plan.requested_by,
                plan.status.value,
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def get_plan(plan_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM plans WHERE plan_id = ?", (plan_id,)).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["parameters"] = json.loads(data["parameters"])
    data["requires_approval"] = bool(data["requires_approval"])
    return data



def list_plans(status: str | None = None) -> list[dict]:
    query, params = "SELECT * FROM plans", ()
    if status is not None:
        query, params = query + " WHERE status = ?", (status,)
    with get_conn() as conn:
        rows = conn.execute(query + " ORDER BY created_at ASC", params).fetchall()
    result = []
    for row in rows:
        data = dict(row)
        data["parameters"] = json.loads(data["parameters"])
        data["requires_approval"] = bool(data["requires_approval"])
        result.append(data)
    return result


def set_decision(plan_id: str, new_status: str, decided_by: str, note: str) -> bool:
    """
    Move a plan out of pending_approval. The WHERE clause makes this atomic:
    if two approvers click at the same moment, only one UPDATE matches a
    still-pending row, so a plan can never be decided twice.
    """
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE plans SET status = ?, decided_by = ?, decision_note = ?, decided_at = ? "
            "WHERE plan_id = ? AND status = 'pending_approval'",
            (new_status, decided_by, note, datetime.now(timezone.utc).isoformat(), plan_id),
        )
        return cur.rowcount == 1



def claim_for_execution(plan_id: str) -> bool:
    """approved -> executed, atomically. Returns False if it was not 'approved'."""
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE plans SET status = 'executed' WHERE plan_id = ? AND status = 'approved'",
            (plan_id,),
        )
        return cur.rowcount == 1
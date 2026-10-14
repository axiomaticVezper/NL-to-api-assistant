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
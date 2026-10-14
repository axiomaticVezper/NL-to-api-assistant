"""
Audit log: one row per lifecycle event, using the shared AuditEvent contract.
Append-only on purpose: there is no update or delete function here.
"""

from contracts.audit_event import AuditEvent, EventType
from contracts.plan import RiskTier

from app.db import get_conn


def log_event(
    plan_id: str,
    event_type: EventType,
    actor: str,
    endpoint: str,
    risk_tier: RiskTier,
    detail: str,
    workflow_id: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        plan_id=plan_id,
        workflow_id=workflow_id,
        event_type=event_type,
        actor=actor,
        endpoint=endpoint,
        risk_tier=risk_tier,
        detail=detail,
    )
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO audit_events VALUES (?,?,?,?,?,?,?,?,?)",
            (
                event.event_id,
                event.plan_id,
                event.workflow_id,
                event.event_type.value,
                event.actor,
                event.endpoint,
                event.risk_tier.value,
                event.detail,
                event.timestamp.isoformat(),
            ),
        )
    return event


def list_events(
    plan_id: str | None = None,
    actor: str | None = None,
    risk_tier: str | None = None,
    event_type: str | None = None,
    limit: int = 100,
) -> list[dict]:
    clauses, params = [], []
    for column, value in (
        ("plan_id", plan_id),
        ("actor", actor),
        ("risk_tier", risk_tier),
        ("event_type", event_type),
    ):
        if value is not None:
            clauses.append(f"{column} = ?")
            params.append(value)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM audit_events {where} ORDER BY timestamp ASC LIMIT ?",
            (*params, limit),
        ).fetchall()
    return [dict(r) for r in rows]
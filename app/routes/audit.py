from fastapi import APIRouter, Depends

from app import audit
from app.auth.rbac import require_roles

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def get_audit_log(
    plan_id: str | None = None,
    actor: str | None = None,
    risk_tier: str | None = None,
    event_type: str | None = None,
    limit: int = 100,
    user: dict = Depends(require_roles("approver", "admin")),
):
    return {"events": audit.list_events(plan_id, actor, risk_tier, event_type, limit)}
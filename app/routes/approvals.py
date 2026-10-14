from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from contracts.audit_event import EventType
from contracts.plan import PlanStatus, RiskTier

from app import audit, plans, policy
from app.auth.rbac import require_roles

router = APIRouter(prefix="/approvals", tags=["approvals"])


class Decision(BaseModel):
    note: str = ""


@router.get("")
def list_pending(user: dict = Depends(require_roles("approver", "admin"))):
    """Pending plans this user is allowed to decide (an approver won't see critical ones)."""
    pending = plans.list_plans(PlanStatus.pending_approval.value)
    return {
        "pending": [p for p in pending if policy.can_decide(user["role"], RiskTier(p["risk_tier"]))]
    }


def _decide(plan_id: str, user: dict, new_status: PlanStatus, event: EventType, note: str):
    record = plans.get_plan(plan_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found")

    tier = RiskTier(record["risk_tier"])
    if not policy.can_decide(user["role"], tier):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Role '{user['role']}' cannot decide '{tier.value}' plans",
        )
    if record["requested_by"] == user["sub"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot decide your own plan")
    if record["status"] != PlanStatus.pending_approval.value:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Plan is already {record['status']}")

    if not plans.set_decision(plan_id, new_status.value, user["sub"], note):
        raise HTTPException(status.HTTP_409_CONFLICT, "Plan was decided by someone else first")

    audit.log_event(plan_id, event, user["sub"], record["endpoint"], tier,
                    note or f"{new_status.value} by {user['sub']}")
    return {"plan_id": plan_id, "status": new_status.value, "decided_by": user["sub"]}


@router.post("/{plan_id}/approve")
def approve(plan_id: str, body: Decision = Decision(),
            user: dict = Depends(require_roles("approver", "admin"))):
    return _decide(plan_id, user, PlanStatus.approved, EventType.approved, body.note)


@router.post("/{plan_id}/reject")
def reject(plan_id: str, body: Decision = Decision(),
           user: dict = Depends(require_roles("approver", "admin"))):
    return _decide(plan_id, user, PlanStatus.rejected, EventType.rejected, body.note)
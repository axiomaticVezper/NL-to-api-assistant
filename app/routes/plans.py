from fastapi import APIRouter, Depends, HTTPException, status

from contracts.audit_event import EventType
from contracts.plan import Plan, PlanStatus

from app import audit, plans, policy
from app.auth.rbac import ROLE_ALLOWED_TIERS, get_current_user

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_plan(plan: Plan, user: dict = Depends(get_current_user)):
    """
    Submit a plan. The server decides everything that matters:
    the real risk tier, whether approval is needed, who requested it, and
    the starting status. Whatever the client sent for those fields is ignored.
    """
    actor, role = user["sub"], user["role"]

    if plans.get_plan(plan.plan_id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A plan with this plan_id already exists")

    def reject(code: int, detail: str):
        audit.log_event(plan.plan_id, EventType.validation_failed, actor,
                        plan.endpoint, plan.risk_tier, detail)
        raise HTTPException(code, detail)

    true_tier = policy.tier_for(plan.method, plan.endpoint)
    if true_tier is None:
        reject(422, f"Unknown endpoint: {plan.method} {plan.endpoint}")
    if plan.risk_tier != true_tier:
        reject(422, f"Plan claims risk tier '{plan.risk_tier.value}' but "
                    f"{plan.method} {plan.endpoint} is '{true_tier.value}'")
    if true_tier not in ROLE_ALLOWED_TIERS.get(role, set()):
        reject(403, f"Role '{role}' is not permitted to request '{true_tier.value}' actions")

    needs_approval = policy.requires_approval(true_tier)
    stored = plan.model_copy(update={
        "requested_by": actor,
        "requires_approval": needs_approval,
        "status": PlanStatus.pending_approval if needs_approval else PlanStatus.approved,
    })
    plans.save_plan(stored)

    audit.log_event(stored.plan_id, EventType.plan_created, actor, stored.endpoint,
                    true_tier, f"Plan submitted: {stored.reason}")
    audit.log_event(stored.plan_id, EventType.validated, "system", stored.endpoint,
                    true_tier, "Endpoint, risk tier and role permission verified")
    if needs_approval:
        audit.log_event(stored.plan_id, EventType.approval_requested, "system",
                        stored.endpoint, true_tier, "Waiting for an approver")

    return {
        "plan_id": stored.plan_id,
        "status": stored.status.value,
        "risk_tier": true_tier.value,
        "requires_approval": needs_approval,
    }


@router.get("/{plan_id}")
def get_plan(plan_id: str, user: dict = Depends(get_current_user)):
    record = plans.get_plan(plan_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found")
    if record["requested_by"] != user["sub"] and user["role"] not in ("approver", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only view your own plans")
    return record
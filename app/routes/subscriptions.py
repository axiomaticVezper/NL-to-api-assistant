from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.rbac import require_risk_tier
from contracts.plan import RiskTier

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

# Mock data — keyed by subscription id, with a customer_id link.
_SUBSCRIPTIONS = {
    "sub_1": {"id": "sub_1", "customer_id": "1", "plan": "pro", "status": "active"},
    "sub_2": {"id": "sub_2", "customer_id": "2", "plan": "basic", "status": "active"},
}


class PlanChangeRequest(BaseModel):
    new_plan: str


@router.get("/{customer_id}")
def get_subscriptions_for_customer(
    customer_id: str, user: dict = Depends(require_risk_tier(RiskTier.read_only))
):
    results = [s for s in _SUBSCRIPTIONS.values() if s["customer_id"] == customer_id]
    return {"results": results}


@router.patch("/{subscription_id}/plan")
def change_plan(
    subscription_id: str,
    body: PlanChangeRequest,
    user: dict = Depends(require_risk_tier(RiskTier.low_risk_write)),
):
    sub = _SUBSCRIPTIONS.get(subscription_id)
    if sub is None:
        return {"error": "not found"}
    sub["plan"] = body.new_plan
    return sub


@router.post("/{subscription_id}/cancel")
def cancel_subscription(
    subscription_id: str, user: dict = Depends(require_risk_tier(RiskTier.high_risk_write))
):
    sub = _SUBSCRIPTIONS.get(subscription_id)
    if sub is None:
        return {"error": "not found"}
    sub["status"] = "cancelled"
    return sub
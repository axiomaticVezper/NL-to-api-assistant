from fastapi import APIRouter, Depends

from app.auth.rbac import require_risk_tier
from contracts.plan import RiskTier

router = APIRouter(prefix="/customers", tags=["customers"])

# Mock data store — stands in for a real DB.
_CUSTOMERS = {
    "1": {"id": "1", "name": "Acme Corp", "email": "billing@acme.com"},
    "2": {"id": "2", "name": "Globex Inc", "email": "ap@globex.com"},
}


@router.get("/search")
def search_customers(email: str, user: dict = Depends(require_risk_tier(RiskTier.read_only))):
    results = [c for c in _CUSTOMERS.values() if c["email"] == email]
    return {"results": results}


@router.get("/{customer_id}")
def get_customer(customer_id: str, user: dict = Depends(require_risk_tier(RiskTier.read_only))):
    customer = _CUSTOMERS.get(customer_id)
    if customer is None:
        return {"error": "not found"}
    return customer


@router.delete("/{customer_id}")
def delete_customer(customer_id: str, user: dict = Depends(require_risk_tier(RiskTier.critical_write))):
    existed = _CUSTOMERS.pop(customer_id, None) is not None
    return {"deleted": existed, "customer_id": customer_id}
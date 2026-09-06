from fastapi import APIRouter, Depends

from app.auth.rbac import require_risk_tier
from contracts.plan import RiskTier

router = APIRouter(prefix="/invoices", tags=["invoices"])

_INVOICES = {
    "inv_1": {"id": "inv_1", "customer_id": "1", "amount": 500, "refunded": False},
    "inv_2": {"id": "inv_2", "customer_id": "2", "amount": 200, "refunded": False},
}


@router.get("/{customer_id}")
def get_invoices_for_customer(
    customer_id: str, user: dict = Depends(require_risk_tier(RiskTier.read_only))
):
    results = [i for i in _INVOICES.values() if i["customer_id"] == customer_id]
    return {"results": results}


@router.post("/{invoice_id}/refund")
def refund_invoice(
    invoice_id: str, user: dict = Depends(require_risk_tier(RiskTier.high_risk_write))
):
    invoice = _INVOICES.get(invoice_id)
    if invoice is None:
        return {"error": "not found"}
    invoice["refunded"] = True
    return invoice


@router.post("/{invoice_id}/refund/reverse")
def reverse_refund(
    invoice_id: str, user: dict = Depends(require_risk_tier(RiskTier.critical_write))
):
    invoice = _INVOICES.get(invoice_id)
    if invoice is None:
        return {"error": "not found"}
    invoice["refunded"] = False
    return invoice
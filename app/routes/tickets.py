from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.rbac import require_risk_tier
from contracts.plan import RiskTier

router = APIRouter(prefix="/tickets", tags=["tickets"])

_TICKETS: list[dict] = []
_next_id = 1


class CreateTicketRequest(BaseModel):
    customer_id: str
    subject: str
    description: str


@router.post("")
def create_ticket(
    body: CreateTicketRequest, user: dict = Depends(require_risk_tier(RiskTier.low_risk_write))
):
    global _next_id
    ticket = {"id": f"ticket_{_next_id}", **body.model_dump(), "created_by": user["sub"]}
    _next_id += 1
    _TICKETS.append(ticket)
    return ticket
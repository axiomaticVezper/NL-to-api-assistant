from fastapi import APIRouter, Depends

from app import compensation
from app.auth.rbac import get_current_user
from app.policy import ENDPOINT_TIERS

router = APIRouter(prefix="/compensations", tags=["compensations"])


@router.get("")
def list_compensations(user: dict = Depends(get_current_user)):
    """Which actions can be undone, how, and which can't (and why)."""
    return {
        "reversible": [
            {"method": m, "endpoint": e, "undo_method": um, "undo_endpoint": ue,
             "undo_risk_tier": ENDPOINT_TIERS[(um, ue)].value}
            for (m, e), (um, ue) in compensation.REVERSIBLE.items()
        ],
        "irreversible": [
            {"method": m, "endpoint": e, "reason": reason}
            for (m, e), reason in compensation.IRREVERSIBLE.items()
        ],
    }
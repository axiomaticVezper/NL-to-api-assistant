from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.rbac import require_risk_tier
from contracts.plan import RiskTier

router = APIRouter(prefix="/teams", tags=["teams"])

_TEAMS = {
    "team_1": {"id": "team_1", "members": ["alice_viewer", "bob_agent"]},
}


class AddMemberRequest(BaseModel):
    user_id: str


@router.get("/{team_id}/members")
def get_team_members(team_id: str, user: dict = Depends(require_risk_tier(RiskTier.read_only))):
    team = _TEAMS.get(team_id)
    if team is None:
        return {"error": "not found"}
    return {"members": team["members"]}


@router.post("/{team_id}/members")
def add_team_member(
    team_id: str,
    body: AddMemberRequest,
    user: dict = Depends(require_risk_tier(RiskTier.low_risk_write)),
):
    team = _TEAMS.get(team_id)
    if team is None:
        return {"error": "not found"}
    if body.user_id not in team["members"]:
        team["members"].append(body.user_id)
    return {"members": team["members"]}


@router.delete("/{team_id}/members/{user_id}")
def remove_team_member(
    team_id: str, user_id: str, user: dict = Depends(require_risk_tier(RiskTier.low_risk_write))
):
    team = _TEAMS.get(team_id)
    if team is None:
        return {"error": "not found"}
    if user_id in team["members"]:
        team["members"].remove(user_id)
    return {"members": team["members"]}
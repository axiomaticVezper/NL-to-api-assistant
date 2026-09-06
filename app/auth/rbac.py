"""
RBAC enforcement — maps risk tiers to allowed roles, and provides a
FastAPI dependency that:
  1. extracts the JWT from the Authorization header
  2. decodes + verifies it
  3. checks the token's role against what this endpoint's risk tier requires
  4. rejects with 401 (bad/missing token) or 403 (valid token, wrong role)

This is enforced server-side on every request — independent of
whatever risk tier Track B's planner *thinks* an action is. That
independence is the whole point of "governed": the planner can be
wrong, buggy, or compromised, and this layer still holds the line.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.auth.jwt_handler import decode_access_token
from contracts.plan import RiskTier

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Per contracts/PHASE0_CONTRACT.md section 2.
# NOTE: built against the *note* under the roles table (agent can request
# high_risk_write but not self-approve), not the summary row, since the
# note is more specific. Flagged as a contract ambiguity to reconcile.
ROLE_ALLOWED_TIERS: dict[str, set[RiskTier]] = {
    "viewer": {RiskTier.read_only},
    "agent": {RiskTier.read_only, RiskTier.low_risk_write, RiskTier.high_risk_write},
    "approver": {RiskTier.read_only, RiskTier.low_risk_write, RiskTier.high_risk_write},
    "admin": {RiskTier.read_only, RiskTier.low_risk_write, RiskTier.high_risk_write, RiskTier.critical_write},
}


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload  # {"sub": username, "role": role, "exp": ...}


def require_risk_tier(tier: RiskTier):
    """
    Returns a FastAPI dependency that enforces a specific risk tier.
    Usage on a route: Depends(require_risk_tier(RiskTier.high_risk_write))
    """
    def _check(user: dict = Depends(get_current_user)) -> dict:
        role = user.get("role")
        allowed = ROLE_ALLOWED_TIERS.get(role, set())
        if tier not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' is not permitted to perform '{tier.value}' actions",
            )
        return user
    return _check
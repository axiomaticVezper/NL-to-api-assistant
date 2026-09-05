"""
JWT creation and verification.

The token's payload carries the username and role — role is what
RBAC checks against on every request, so it must be tamper-proof.
That's exactly what JWT signing guarantees: nobody can forge a
"role": "admin" claim without knowing SECRET_KEY.
"""

from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt

# In real deployment this MUST come from an env var / secrets manager,
# never hardcoded. Fine as a constant for Phase 1 mock purposes.
SECRET_KEY = "phase1-dev-secret-change-me"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": username,   # "sub" = subject, JWT-standard claim for "who is this token about"
        "role": role,
        "exp": expire,      # JWT-standard claim, jose checks this automatically on decode
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """
    Returns the payload dict if the token is valid and unexpired,
    otherwise None. Callers (RBAC dependency) treat None as "reject".
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
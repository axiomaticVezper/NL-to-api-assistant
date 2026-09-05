"""
Mock user store for Phase 1.
In a real system this would be a database table. For now, a fixed
dict is enough to exercise auth + RBAC end-to-end.

Password for every mock user is: "password123"
(We hash it below rather than storing plaintext, even in mock data —
good habit to carry forward, and it lets us test the real hashing/verify flow.)
"""

import bcrypt

_MOCK_PASSWORD = "password123"
_HASHED_PASSWORD = bcrypt.hashpw(_MOCK_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

# username -> user record
USERS = {
    "alice_viewer": {
        "username": "alice_viewer",
        "hashed_password": _HASHED_PASSWORD,
        "role": "viewer",
    },
    "bob_agent": {
        "username": "bob_agent",
        "hashed_password": _HASHED_PASSWORD,
        "role": "agent",
    },
    "carol_approver": {
        "username": "carol_approver",
        "hashed_password": _HASHED_PASSWORD,
        "role": "approver",
    },
    "dave_admin": {
        "username": "dave_admin",
        "hashed_password": _HASHED_PASSWORD,
        "role": "admin",
    },
}


def get_user(username: str) -> dict | None:
    return USERS.get(username)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
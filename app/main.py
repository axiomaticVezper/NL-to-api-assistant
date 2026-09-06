from fastapi import FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends

from app.auth.users import get_user, verify_password
from app.auth.jwt_handler import create_access_token
from app.routes import customers, subscriptions, invoices, teams, tickets

app = FastAPI(title="NL-to-API Assistant — Mock API (Phase 1, Track A)")


@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Mock login. form_data.username / form_data.password come from a
    standard OAuth2 password-grant form (username + password fields),
    which is what OAuth2PasswordBearer expects on the other end.
    """
    user = get_user(form_data.username)
    if user is None or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(username=user["username"], role=user["role"])
    return {"access_token": token, "token_type": "bearer"}


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(customers.router)
app.include_router(subscriptions.router)
app.include_router(invoices.router)
app.include_router(teams.router)
app.include_router(tickets.router)
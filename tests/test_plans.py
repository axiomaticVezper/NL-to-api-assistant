from app import audit, policy
from app.main import app


def plan_body(endpoint="/subscriptions/{subscription_id}/cancel", method="POST",
              tier="high_risk_write", **extra):
    body = {
        "endpoint": endpoint,
        "method": method,
        "parameters": {"subscription_id": "sub_1"},
        "reason": "customer asked to cancel",
        "expected_result": "subscription cancelled",
        "risk_tier": tier,
        "requires_approval": True,
        "requested_by": "someone_else",
    }
    body.update(extra)
    return body


def test_high_risk_plan_becomes_pending(client, as_user):
    r = client.post("/plans", json=plan_body(), headers=as_user("bob_agent"))
    assert r.status_code == 201
    assert r.json()["status"] == "pending_approval"
    assert r.json()["requires_approval"] is True


def test_low_risk_plan_is_cleared_without_approval(client, as_user):
    body = plan_body("/tickets", "POST", "low_risk_write", requires_approval=True)
    r = client.post("/plans", json=body, headers=as_user("bob_agent"))
    assert r.status_code == 201
    assert r.json()["status"] == "approved"
    assert r.json()["requires_approval"] is False  # server decided, not the client


def test_client_cannot_self_approve_by_setting_status(client, as_user):
    body = plan_body(status="approved", requires_approval=False)
    r = client.post("/plans", json=body, headers=as_user("bob_agent"))
    assert r.json()["status"] == "pending_approval"


def test_requested_by_comes_from_token_not_body(client, as_user):
    h = as_user("bob_agent")
    plan_id = client.post("/plans", json=plan_body(), headers=h).json()["plan_id"]
    assert client.get(f"/plans/{plan_id}", headers=h).json()["requested_by"] == "bob_agent"


def test_viewer_denied_at_plan_time(client, as_user):
    r = client.post("/plans", json=plan_body(), headers=as_user("alice_viewer"))
    assert r.status_code == 403
    events = audit.list_events(event_type="validation_failed")
    assert len(events) == 1 and events[0]["actor"] == "alice_viewer"


def test_agent_cannot_request_critical(client, as_user):
    body = plan_body("/customers/{customer_id}", "DELETE", "critical_write")
    assert client.post("/plans", json=body, headers=as_user("bob_agent")).status_code == 403


def test_lying_about_risk_tier_is_rejected(client, as_user):
    body = plan_body(tier="read_only", requires_approval=False)
    r = client.post("/plans", json=body, headers=as_user("bob_agent"))
    assert r.status_code == 422
    assert "claims risk tier" in r.json()["detail"]


def test_unknown_endpoint_rejected(client, as_user):
    body = plan_body("/nope", "GET", "read_only")
    assert client.post("/plans", json=body, headers=as_user("bob_agent")).status_code == 422


def test_duplicate_plan_id_conflicts(client, as_user):
    h = as_user("bob_agent")
    body = plan_body(plan_id="fixed-id")
    assert client.post("/plans", json=body, headers=h).status_code == 201
    assert client.post("/plans", json=body, headers=h).status_code == 409


def test_audit_trail_for_pending_plan(client, as_user):
    plan_id = client.post("/plans", json=plan_body(), headers=as_user("bob_agent")).json()["plan_id"]
    types = [e["event_type"] for e in audit.list_events(plan_id=plan_id)]
    assert types == ["plan_created", "validated", "approval_requested"]


def test_only_requester_or_approver_can_view_plan(client, as_user):
    plan_id = client.post("/plans", json=plan_body(), headers=as_user("bob_agent")).json()["plan_id"]
    assert client.get(f"/plans/{plan_id}", headers=as_user("alice_viewer")).status_code == 403
    assert client.get(f"/plans/{plan_id}", headers=as_user("carol_approver")).status_code == 200


GOVERNED_EXCLUDED = {
    "/auth/login", "/health", "/audit", "/plans", "/plans/{plan_id}",
    "/approvals", "/approvals/{plan_id}/approve", "/approvals/{plan_id}/reject",
"/compensations"
}


def test_policy_lists_exactly_the_governed_endpoints():
    paths = app.openapi()["paths"]
    real = {
        (method.upper(), path)
        for path, methods in paths.items()
        if path not in GOVERNED_EXCLUDED
        for method in methods
    }
    assert real == set(policy.ENDPOINT_TIERS)


def test_policy_matches_real_route_behavior(client, as_user):
    """
    For every endpoint and every role, the real route must answer 403 exactly
    when ROLE_ALLOWED_TIERS says the role may not use that tier. This catches
    policy.py drifting away from the guards written on the routes.
    """
    from app.auth.rbac import ROLE_ALLOWED_TIERS

    users = {"viewer": "alice_viewer", "agent": "bob_agent",
             "approver": "carol_approver", "admin": "dave_admin"}
    for (method, template), tier in policy.ENDPOINT_TIERS.items():
        path = template.replace("{", "").replace("}", "")  # e.g. {customer_id} -> customer_id
        for role, username in users.items():
            r = client.request(method, path, headers=as_user(username))
            expect_forbidden = tier not in ROLE_ALLOWED_TIERS[role]
            assert (r.status_code == 403) == expect_forbidden, (method, template, role, r.status_code)
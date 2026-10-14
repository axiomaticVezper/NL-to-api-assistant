from app import audit
from tests.test_plans import plan_body


def submit(client, headers, **kw):
    r = client.post("/plans", json=plan_body(**kw), headers=headers)
    assert r.status_code == 201
    return r.json()["plan_id"]


def critical(client, headers):
    return submit(client, headers, endpoint="/customers/{customer_id}",
                  method="DELETE", tier="critical_write")


def test_approver_approves_high_risk_plan(client, as_user):
    plan_id = submit(client, as_user("bob_agent"))
    r = client.post(f"/approvals/{plan_id}/approve", json={"note": "looks fine"},
                    headers=as_user("carol_approver"))
    assert r.status_code == 200 and r.json()["status"] == "approved"
    stored = client.get(f"/plans/{plan_id}", headers=as_user("bob_agent")).json()
    assert stored["status"] == "approved" and stored["decided_by"] == "carol_approver"
    last = audit.list_events(plan_id=plan_id)[-1]
    assert last["event_type"] == "approved" and last["actor"] == "carol_approver"


def test_reject_records_reason(client, as_user):
    plan_id = submit(client, as_user("bob_agent"))
    r = client.post(f"/approvals/{plan_id}/reject", json={"note": "wrong customer"},
                    headers=as_user("carol_approver"))
    assert r.json()["status"] == "rejected"
    last = audit.list_events(plan_id=plan_id)[-1]
    assert last["event_type"] == "rejected" and last["detail"] == "wrong customer"


def test_viewer_and_agent_cannot_decide(client, as_user):
    plan_id = submit(client, as_user("bob_agent"))
    assert client.post(f"/approvals/{plan_id}/approve", headers=as_user("alice_viewer")).status_code == 403
    assert client.post(f"/approvals/{plan_id}/approve", headers=as_user("bob_agent")).status_code == 403


def test_nobody_can_approve_their_own_plan(client, as_user):
    h = as_user("carol_approver")
    plan_id = submit(client, h)  # approvers may request high-risk actions
    r = client.post(f"/approvals/{plan_id}/approve", headers=h)
    assert r.status_code == 403 and "own plan" in r.json()["detail"]


def test_plan_cannot_be_decided_twice(client, as_user):
    plan_id = submit(client, as_user("bob_agent"))
    assert client.post(f"/approvals/{plan_id}/approve", headers=as_user("carol_approver")).status_code == 200
    assert client.post(f"/approvals/{plan_id}/reject", headers=as_user("dave_admin")).status_code == 409


def test_critical_plan_needs_a_different_admin(client, as_user):
    plan_id = critical(client, as_user("dave_admin"))
    assert client.post(f"/approvals/{plan_id}/approve", headers=as_user("carol_approver")).status_code == 403
    assert client.post(f"/approvals/{plan_id}/approve", headers=as_user("dave_admin")).status_code == 403
    assert client.post(f"/approvals/{plan_id}/approve", headers=as_user("erin_admin")).status_code == 200


def test_unknown_plan_is_404(client, as_user):
    assert client.post("/approvals/nope/approve", headers=as_user("carol_approver")).status_code == 404


def test_pending_list_respects_role(client, as_user):
    high = submit(client, as_user("bob_agent"))
    crit = critical(client, as_user("dave_admin"))
    approver_view = client.get("/approvals", headers=as_user("carol_approver")).json()["pending"]
    admin_view = client.get("/approvals", headers=as_user("erin_admin")).json()["pending"]
    assert [p["plan_id"] for p in approver_view] == [high]
    assert {p["plan_id"] for p in admin_view} == {high, crit}
    assert client.get("/approvals", headers=as_user("bob_agent")).status_code == 403


def test_full_audit_trail_of_an_approval(client, as_user):
    plan_id = submit(client, as_user("bob_agent"))
    client.post(f"/approvals/{plan_id}/approve", headers=as_user("carol_approver"))
    types = [e["event_type"] for e in audit.list_events(plan_id=plan_id)]
    assert types == ["plan_created", "validated", "approval_requested", "approved"]
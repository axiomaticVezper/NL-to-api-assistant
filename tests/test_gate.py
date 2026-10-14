from app import audit
from tests.test_plans import plan_body


def approved_plan(client, as_user, requester="bob_agent", approver="carol_approver", **kw):
    r = client.post("/plans", json=plan_body(**kw), headers=as_user(requester))
    plan_id = r.json()["plan_id"]
    assert client.post(f"/approvals/{plan_id}/approve", headers=as_user(approver)).status_code == 200
    return plan_id


def use(client, headers, plan_id, method="POST", path="/subscriptions/sub_1/cancel"):
    return client.request(method, path, headers={**headers, "X-Plan-Id": plan_id})


def test_direct_call_without_plan_is_blocked(client, as_user):
    r = client.post("/subscriptions/sub_1/cancel", headers=as_user("bob_agent"))
    assert r.status_code == 428


def test_full_flow_submit_approve_execute(client, as_user):
    h = as_user("bob_agent")
    plan_id = client.post("/plans", json=plan_body(), headers=h).json()["plan_id"]
    assert use(client, h, plan_id).status_code == 409          # still pending
    client.post(f"/approvals/{plan_id}/approve", headers=as_user("carol_approver"))
    r = use(client, h, plan_id)                                  # now it works
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
    assert client.get(f"/plans/{plan_id}", headers=h).json()["status"] == "executed"
    types = [e["event_type"] for e in audit.list_events(plan_id=plan_id)]
    assert types[-2:] == ["approved", "executed"]


def test_approved_plan_is_single_use(client, as_user):
    h = as_user("bob_agent")
    plan_id = approved_plan(client, as_user)
    assert use(client, h, plan_id).status_code == 200
    assert use(client, h, plan_id).status_code == 409


def test_rejected_plan_cannot_be_used(client, as_user):
    h = as_user("bob_agent")
    plan_id = client.post("/plans", json=plan_body(), headers=h).json()["plan_id"]
    client.post(f"/approvals/{plan_id}/reject", headers=as_user("carol_approver"))
    assert use(client, h, plan_id).status_code == 409


def test_plan_belongs_to_its_requester(client, as_user):
    plan_id = approved_plan(client, as_user)  # bob's plan
    r = use(client, as_user("carol_approver"), plan_id)  # carol may do high-risk, but not bob's plan
    assert r.status_code == 403


def test_plan_for_sub_1_cannot_cancel_sub_2(client, as_user):
    plan_id = approved_plan(client, as_user)
    r = use(client, as_user("bob_agent"), plan_id, path="/subscriptions/sub_2/cancel")
    assert r.status_code == 403 and "sub_1" in r.json()["detail"]


def test_plan_cannot_be_used_on_a_different_endpoint(client, as_user):
    plan_id = approved_plan(client, as_user)
    r = use(client, as_user("bob_agent"), plan_id, path="/invoices/inv_1/refund")
    assert r.status_code == 403


def test_unknown_plan_id_is_refused(client, as_user):
    assert use(client, as_user("bob_agent"), "does-not-exist").status_code == 403


def test_critical_flow_with_two_admins(client, as_user):
    plan_id = approved_plan(
        client, as_user, requester="dave_admin", approver="erin_admin",
        endpoint="/customers/{customer_id}", method="DELETE", tier="critical_write",
        parameters={"customer_id": "1"},
    )
    r = use(client, as_user("dave_admin"), plan_id, method="DELETE", path="/customers/1")
    assert r.status_code == 200


def test_low_risk_endpoints_still_work_directly(client, as_user):
    r = client.post("/tickets", headers=as_user("bob_agent"),
                    json={"customer_id": "1", "subject": "hi", "description": "x"})
    assert r.status_code == 200
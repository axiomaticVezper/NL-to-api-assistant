from app import idempotency
from app.routes import tickets
from tests.test_gate import approved_plan, use
from tests.test_plans import plan_body

TICKET = {"customer_id": "1", "subject": "printer on fire", "description": "urgent"}


def new_ticket(client, headers, key=None, body=TICKET):
    if key:
        headers = {**headers, "Idempotency-Key": key}
    return client.post("/tickets", json=body, headers=headers)


def test_same_key_twice_creates_only_one_ticket(client, as_user):
    h = as_user("bob_agent")
    before = len(tickets._TICKETS)
    first = new_ticket(client, h, key="abc-1")
    second = new_ticket(client, h, key="abc-1")
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()                  # same ticket id returned
    assert len(tickets._TICKETS) == before + 1            # ...and only ONE was created
    assert second.headers["Idempotent-Replay"] == "true"
    assert "Idempotent-Replay" not in first.headers


def test_without_a_key_every_call_creates_a_ticket(client, as_user):
    h = as_user("bob_agent")
    before = len(tickets._TICKETS)
    new_ticket(client, h)
    new_ticket(client, h)
    assert len(tickets._TICKETS) == before + 2


def test_different_keys_are_different_requests(client, as_user):
    h = as_user("bob_agent")
    before = len(tickets._TICKETS)
    new_ticket(client, h, key="k-a")
    new_ticket(client, h, key="k-b")
    assert len(tickets._TICKETS) == before + 2


def test_same_key_with_different_body_is_refused(client, as_user):
    h = as_user("bob_agent")
    new_ticket(client, h, key="abc-2")
    r = new_ticket(client, h, key="abc-2", body={**TICKET, "subject": "something else"})
    assert r.status_code == 422


def test_keys_are_scoped_per_user(client, as_user):
    before = len(tickets._TICKETS)
    a = new_ticket(client, as_user("bob_agent"), key="shared")
    b = new_ticket(client, as_user("carol_approver"), key="shared")
    assert a.json()["id"] != b.json()["id"]
    assert len(tickets._TICKETS) == before + 2


def test_retrying_an_executed_plan_with_same_key_returns_original_result(client, as_user):
    h = as_user("bob_agent")
    plan_id = approved_plan(client, as_user)
    headers = {**h, "Idempotency-Key": "cancel-sub-1"}
    first = use(client, headers, plan_id)
    retry = use(client, headers, plan_id)
    assert first.status_code == retry.status_code == 200      # retry is NOT an error
    assert retry.headers["Idempotent-Replay"] == "true"
    assert use(client, h, plan_id).status_code == 409         # no key => plan already used


def test_failed_attempts_are_not_remembered(client, as_user):
    h = as_user("bob_agent")
    r = client.post("/plans", json=plan_body(), headers=h)
    plan_id = r.json()["plan_id"]
    headers = {**h, "Idempotency-Key": "retry-me"}
    assert use(client, headers, plan_id).status_code == 409   # not approved yet
    client.post(f"/approvals/{plan_id}/approve", headers=as_user("carol_approver"))
    assert use(client, headers, plan_id).status_code == 200   # same key now succeeds


def test_begin_complete_lifecycle():
    assert idempotency.begin("u", "k", "fp1")[0] == "new"
    assert idempotency.begin("u", "k", "fp1")[0] == "in_progress"   # still running
    idempotency.complete("u", "k", 200, b"{}", "application/json")
    assert idempotency.begin("u", "k", "fp1")[0] == "replay"
    assert idempotency.begin("u", "k", "other")[0] == "mismatch"


def test_stale_in_progress_claim_is_released():
    from datetime import timedelta
    from app.db import get_conn
    idempotency.begin("u", "stuck", "fp")
    old = (idempotency._now() - timedelta(minutes=5)).isoformat()
    with get_conn() as conn:
        conn.execute("UPDATE idempotency_keys SET created_at = ? WHERE key = 'stuck'", (old,))
    assert idempotency.begin("u", "stuck", "fp")[0] == "new"       # crashed claim was cleaned up
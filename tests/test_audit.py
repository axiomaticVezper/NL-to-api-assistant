from contracts.audit_event import EventType
from contracts.plan import RiskTier

from app import audit


def _log(plan_id="p1", actor="bob_agent", event_type=EventType.plan_created, tier=RiskTier.read_only):
    return audit.log_event(plan_id, event_type, actor, "/customers/1", tier, "test detail")


def test_log_and_list_roundtrip():
    _log()
    events = audit.list_events()
    assert len(events) == 1
    assert events[0]["plan_id"] == "p1"
    assert events[0]["event_type"] == "plan_created"


def test_filters_work():
    _log(plan_id="p1", actor="bob_agent")
    _log(plan_id="p2", actor="carol_approver", event_type=EventType.approved, tier=RiskTier.high_risk_write)
    assert len(audit.list_events(plan_id="p2")) == 1
    assert len(audit.list_events(actor="bob_agent")) == 1
    assert len(audit.list_events(risk_tier="high_risk_write")) == 1
    assert len(audit.list_events(event_type="approved")) == 1


def test_audit_endpoint_blocks_viewer_and_agent(client, as_user):
    assert client.get("/audit", headers=as_user("alice_viewer")).status_code == 403
    assert client.get("/audit", headers=as_user("bob_agent")).status_code == 403


def test_audit_endpoint_allows_approver_and_sees_events(client, as_user):
    _log()
    r = client.get("/audit", headers=as_user("carol_approver"))
    assert r.status_code == 200
    assert len(r.json()["events"]) == 1


def test_audit_endpoint_requires_login(client):
    assert client.get("/audit").status_code == 401
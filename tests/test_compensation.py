import pytest

from contracts.plan import RiskTier

from app import compensation, policy


def test_refund_is_undone_by_reverse_refund_and_needs_critical_approval():
    undo = compensation.propose_compensation(
        "POST", "/invoices/{invoice_id}/refund", {"invoice_id": "inv_1"})
    assert undo == {
        "method": "POST",
        "endpoint": "/invoices/{invoice_id}/refund/reverse",
        "parameters": {"invoice_id": "inv_1"},
        "risk_tier": "critical_write",
    }


def test_adding_a_team_member_is_undone_by_removing_them():
    undo = compensation.propose_compensation(
        "POST", "/teams/{team_id}/members", {"team_id": "team_1", "user_id": "bob_agent"})
    assert undo["method"] == "DELETE"
    assert undo["endpoint"] == "/teams/{team_id}/members/{user_id}"
    assert undo["parameters"] == {"team_id": "team_1", "user_id": "bob_agent"}


def test_removing_a_member_is_undone_by_re_adding_them():
    undo = compensation.propose_compensation(
        "DELETE", "/teams/{team_id}/members/{user_id}", {"team_id": "team_1", "user_id": "bob_agent"})
    assert (undo["method"], undo["endpoint"]) == ("POST", "/teams/{team_id}/members")
    assert undo["parameters"]["user_id"] == "bob_agent"   # the re-add needs it in the body


def test_irreversible_action_has_no_compensation():
    assert compensation.propose_compensation(
        "DELETE", "/customers/{customer_id}", {"customer_id": "1"}) is None


def test_missing_parameter_is_reported():
    with pytest.raises(ValueError, match="invoice_id"):
        compensation.propose_compensation("POST", "/invoices/{invoice_id}/refund", {})


def test_every_write_endpoint_is_classified_exactly_once():
    """Adding a new write endpoint without deciding how to undo it fails this test."""
    writes = {k for k, tier in policy.ENDPOINT_TIERS.items() if tier != RiskTier.read_only}
    reversible, irreversible = set(compensation.REVERSIBLE), set(compensation.IRREVERSIBLE)
    assert reversible | irreversible == writes
    assert reversible & irreversible == set()


def test_every_undo_target_is_a_real_governed_endpoint():
    for undo in compensation.REVERSIBLE.values():
        assert undo in policy.ENDPOINT_TIERS


def test_compensation_endpoint_lists_both_kinds(client, as_user):
    assert client.get("/compensations").status_code == 401
    body = client.get("/compensations", headers=as_user("alice_viewer")).json()
    assert len(body["reversible"]) == 4 and len(body["irreversible"]) == 4
    refund = next(r for r in body["reversible"] if r["endpoint"].endswith("/refund"))
    assert refund["undo_risk_tier"] == "critical_write"
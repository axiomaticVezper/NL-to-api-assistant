"""
Compensating actions: for every write endpoint, how to UNDO it, or why we can't.

Phase 3's rollback will read this table. Note that an undo is not executed
directly: it becomes a NEW plan that goes through the same governance as any
other action (risk tier, approval, audit). For example, undoing a refund means
calling reverse_refund, which is critical_write, so it needs two admins.

Every write endpoint must appear in exactly one of the two tables below. A test
enforces that, so adding a new endpoint forces someone to decide how (or whether)
it can be undone.
"""

import re

from app.policy import ENDPOINT_TIERS

# (method, path) -> (method, path) of the action that undoes it
REVERSIBLE: dict[tuple[str, str], tuple[str, str]] = {
    ("POST", "/invoices/{invoice_id}/refund"): ("POST", "/invoices/{invoice_id}/refund/reverse"),
    ("POST", "/invoices/{invoice_id}/refund/reverse"): ("POST", "/invoices/{invoice_id}/refund"),
    ("POST", "/teams/{team_id}/members"): ("DELETE", "/teams/{team_id}/members/{user_id}"),
    ("DELETE", "/teams/{team_id}/members/{user_id}"): ("POST", "/teams/{team_id}/members"),
}

# (method, path) -> why it cannot be undone
IRREVERSIBLE: dict[tuple[str, str], str] = {
    ("DELETE", "/customers/{customer_id}"): "A deleted customer cannot be restored.",
    ("POST", "/subscriptions/{subscription_id}/cancel"): "There is no reactivate endpoint yet.",
    ("PATCH", "/subscriptions/{subscription_id}/plan"):
        "Undo needs the previous plan, which must be captured before executing (Phase 3 executor).",
    ("POST", "/tickets"): "There is no endpoint to delete a ticket.",
}


def propose_compensation(method: str, endpoint: str, parameters: dict) -> dict | None:
    """
    Returns the fields of a plan that would undo (method, endpoint), or None if
    the action is irreversible. Raises ValueError if a needed parameter is missing.
    """
    target = REVERSIBLE.get((method.upper(), endpoint))
    if target is None:
        return None
    undo_method, undo_endpoint = target
    needed = set(re.findall(r"{(\w+)}", undo_endpoint))
    missing = needed - parameters.keys()
    if missing:
        raise ValueError(f"Cannot build the undo action: missing {sorted(missing)}")
    return {
        "method": undo_method,
        "endpoint": undo_endpoint,
        "parameters": dict(parameters),
        "risk_tier": ENDPOINT_TIERS[target].value,
    }
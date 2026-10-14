"""
Server-side policy: the ONE place the server decides how risky an endpoint is.
The server never trusts a risk tier (or requires_approval flag) sent by a client
or by the planner. It looks the tier up here, by (method, path template).

The paths use the same {placeholder} names as the OpenAPI schema, because that
is what Track B's planner sends in Plan.endpoint.
"""

from contracts.plan import RiskTier

ENDPOINT_TIERS: dict[tuple[str, str], RiskTier] = {
    ("GET", "/customers/search"): RiskTier.read_only,
    ("GET", "/customers/{customer_id}"): RiskTier.read_only,
    ("DELETE", "/customers/{customer_id}"): RiskTier.critical_write,
    ("GET", "/subscriptions/{customer_id}"): RiskTier.read_only,
    ("PATCH", "/subscriptions/{subscription_id}/plan"): RiskTier.low_risk_write,
    ("POST", "/subscriptions/{subscription_id}/cancel"): RiskTier.high_risk_write,
    ("GET", "/invoices/{customer_id}"): RiskTier.read_only,
    ("POST", "/invoices/{invoice_id}/refund"): RiskTier.high_risk_write,
    ("POST", "/invoices/{invoice_id}/refund/reverse"): RiskTier.critical_write,
    ("GET", "/teams/{team_id}/members"): RiskTier.read_only,
    ("POST", "/teams/{team_id}/members"): RiskTier.low_risk_write,
    ("DELETE", "/teams/{team_id}/members/{user_id}"): RiskTier.low_risk_write,
    ("POST", "/tickets"): RiskTier.low_risk_write,
}

APPROVAL_REQUIRED_TIERS = {RiskTier.high_risk_write, RiskTier.critical_write}


def tier_for(method: str, endpoint: str) -> RiskTier | None:
    return ENDPOINT_TIERS.get((method.upper(), endpoint))


def requires_approval(tier: RiskTier) -> bool:
    return tier in APPROVAL_REQUIRED_TIERS
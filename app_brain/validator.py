from contracts.plan import Plan
from app_brain.schema_parser import Endpoint

class ValidationError(Exception):
    pass

def validate_plan(plan: Plan, endpoints: list[Endpoint]) -> None:
    """Raises ValidationError if the plan is structurally invalid. Returns None if valid."""

    matched = next(
        (e for e in endpoints if e.path == plan.endpoint and e.method == plan.method),
        None,
    )
    if matched is None:
        raise ValidationError(
            f"Plan references an endpoint that doesn't exist: {plan.method} {plan.endpoint}"
        )

    if matched.risk_tier != plan.risk_tier.value:
        raise ValidationError(
            f"Plan's risk_tier ({plan.risk_tier.value}) doesn't match the endpoint's "
            f"actual risk_tier ({matched.risk_tier}) — possible tampering or stale data"
        )

    required_params = {p.name for p in matched.params if p.required}
    provided_params = set(plan.parameters.keys())
    missing = required_params - provided_params
    if missing:
        raise ValidationError(f"Missing required parameters: {missing}")

    for param in matched.params:
        if param.name in plan.parameters and plan.parameters[param.name] == "":
            raise ValidationError(f"Parameter '{param.name}' was extracted as empty")

if __name__ == "__main__":
    from app_brain.schema_parser import load_endpoints
    from app_brain.retriever import get_candidates
    from app_brain.planner import create_plan

    endpoints = load_endpoints("openapi_live.json", "stubs/risk_tiers.json")
    request = "cancel John's subscription, his id is sub_123"
    candidates = get_candidates(request, endpoints)
    plan = create_plan(request, candidates, requested_by="bob_agent")

    try:
        validate_plan(plan, endpoints)
        print("✅ Plan is valid")
        print(plan.model_dump_json(indent=2))
    except ValidationError as e:
        print(f"❌ Validation failed: {e}")
        
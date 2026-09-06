import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

from contracts.plan import Plan, RiskTier
from app_brain.schema_parser import Endpoint

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

PLAN_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "endpoint": {"type": "string"},
        "method": {"type": "string"},
        "parameters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["name", "value"],
            },
        },
        "reason": {"type": "string"},
        "expected_result": {"type": "string"},
    },
    "required": ["endpoint", "method", "parameters", "reason", "expected_result"],
}
def build_prompt(request: str, candidates: list[Endpoint]) -> str:
    candidate_lines = []
    for c in candidates:
        param_names = [p.name for p in c.params]
        candidate_lines.append(
            f"- {c.method} {c.path} ({c.risk_tier}): {c.summary}\n"
            f"  Required parameter names: {param_names if param_names else 'none'}"
        )
    candidate_desc = "\n".join(candidate_lines)

    return (
        f"User request: \"{request}\"\n\n"
        f"Available candidate endpoints:\n{candidate_desc}\n\n"
        "Pick the single best endpoint for this request. "
        "In the \"parameters\" field, you MUST include a key for every parameter "
        "name listed for that endpoint, with its value extracted from the user request. "
        "If a value genuinely cannot be found in the request, use an empty string, "
        "never omit the key. Respond only with the requested JSON."
    )

def create_plan(request: str, candidates: list[Endpoint], requested_by: str) -> Plan:
    if not candidates:
        raise ValueError("No candidate endpoints found for this request")

    prompt = build_prompt(request, candidates)

    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=PLAN_JSON_SCHEMA,
        ),
    )
    raw = json.loads(response.text)
    raw["parameters"] = {p["name"]: p["value"] for p in raw["parameters"]}

    matched = next(
        (c for c in candidates if c.path == raw["endpoint"] and c.method == raw["method"]),
        None,
    )
    if matched is None:
        raise ValueError(f"LLM picked an endpoint not in candidates: {raw['endpoint']} {raw['method']}")

    risk_tier = RiskTier(matched.risk_tier)
    requires_approval = risk_tier in (RiskTier.high_risk_write, RiskTier.critical_write)

    return Plan(
        endpoint=raw["endpoint"],
        method=raw["method"],
        parameters=raw["parameters"],
        reason=raw["reason"],
        expected_result=raw["expected_result"],
        risk_tier=risk_tier,
        requires_approval=requires_approval,
        requested_by=requested_by,
    )

if __name__ == "__main__":
    from app_brain.schema_parser import load_endpoints
    from app_brain.retriever import get_candidates

    endpoints = load_endpoints("openapi_live.json", "stubs/risk_tiers.json")
    request = "cancel John's subscription, his id is sub_123"
    candidates = get_candidates(request, endpoints)

    plan = create_plan(request, candidates, requested_by="bob_agent")
    print(plan.model_dump_json(indent=2))
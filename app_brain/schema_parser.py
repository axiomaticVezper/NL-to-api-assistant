import json
from pathlib import Path
from pydantic import BaseModel

class EndpointParam(BaseModel):
    name: str
    location: str          # "path" | "query"
    required: bool
    type: str

class Endpoint(BaseModel):
    path: str
    method: str
    summary: str
    params: list[EndpointParam]
    risk_tier: str | None
    requires_auth: bool

def _param_from_openapi(p: dict) -> EndpointParam:
    return EndpointParam(
        name=p["name"],
        location=p["in"],
        required=p.get("required", False),
        type=p.get("schema", {}).get("type", "string"),
    )

def load_endpoints(openapi_path: str, risk_tiers_path: str) -> list[Endpoint]:
    openapi = json.loads(Path(openapi_path).read_text())
    risk_tiers = json.loads(Path(risk_tiers_path).read_text())

    endpoints = []
    for path, methods in openapi["paths"].items():
        for method, spec in methods.items():
            method_upper = method.upper()
            key = f"{method_upper} {path}"
            params = [_param_from_openapi(p) for p in spec.get("parameters", [])]
            endpoints.append(Endpoint(
                path=path,
                method=method_upper,
                summary=spec.get("summary", ""),
                params=params,
                risk_tier=risk_tiers.get(key),   # None if not found — flagged below
                requires_auth="security" in spec,
            ))
    return endpoints

if __name__ == "__main__":
    endpoints = load_endpoints("openapi_live.json", "stubs/risk_tiers.json")
    for e in endpoints:
        flag = " ⚠ NO RISK TIER" if e.risk_tier is None else ""
        print(f"{e.method:6} {e.path:45} {e.risk_tier or '':16}{flag}")
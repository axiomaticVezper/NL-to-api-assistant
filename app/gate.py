"""
The approval gate. High-risk and critical endpoints refuse to run unless the
caller presents an approved plan in the X-Plan-Id header. Without this, an
agent could skip the approval queue by calling the endpoint directly.

An approved plan is a ONE-TIME ticket, valid only for:
  - the person who requested it,
  - the exact endpoint + method it was approved for,
  - the exact path parameters it was approved with (so a plan approved for
    sub_1 cannot be used to cancel sub_2).
"""

from fastapi import HTTPException, Request

from contracts.audit_event import EventType
from contracts.plan import RiskTier

from app import audit, plans


def enforce_approved_plan(request: Request, user: dict, tier: RiskTier) -> None:
    plan_id = request.headers.get("x-plan-id")
    if not plan_id:
        raise HTTPException(
            428, "This action requires an approved plan. Submit one to POST /plans, "
                 "get it approved, then send its id in the X-Plan-Id header."
        )

    record = plans.get_plan(plan_id)
    route_path = request.scope["route"].path  # the template, e.g. /subscriptions/{subscription_id}/cancel

    def deny(code: int, detail: str):
        if record is not None:  # only log against plans that really exist
            audit.log_event(plan_id, EventType.validation_failed, user["sub"],
                            route_path, tier, detail)
        raise HTTPException(code, detail)

    if record is None:
        deny(403, "Unknown plan")
    if record["requested_by"] != user["sub"]:
        deny(403, "This plan was requested by someone else")
    if (record["method"].upper(), record["endpoint"]) != (request.method, route_path):
        deny(403, f"This plan was approved for {record['method']} {record['endpoint']}, "
                  f"not {request.method} {route_path}")
    for name, value in request.path_params.items():
        if str(record["parameters"].get(name)) != str(value):
            deny(403, f"Plan was approved for {name}={record['parameters'].get(name)!r}, "
                      f"not {value!r}")
    if record["status"] != "approved":
        deny(409, f"Plan is '{record['status']}', it must be 'approved'")
    if not plans.claim_for_execution(plan_id):
        deny(409, "Plan was already used")

    audit.log_event(plan_id, EventType.executed, user["sub"], route_path, tier,
                    f"Executed {request.method} {request.url.path}")
"""
End-to-end demo of the governed flow against a RUNNING server.

    1) start the server:   uvicorn app.main:app --reload
    2) in another terminal: python scripts/demo_flow.py

It walks: direct call blocked -> submit plan -> pending -> approve ->
execute with the approved plan -> safe retry -> single-use check -> audit trail.
"""

import sys
import uuid

import httpx

BASE = "http://127.0.0.1:8000"
client = httpx.Client(base_url=BASE, timeout=10)
failures = 0


def check(label: str, response: httpx.Response, expected: int):
    global failures
    ok = response.status_code == expected
    failures += 0 if ok else 1
    print(f"[{'OK' if ok else 'FAIL'}] {label}: HTTP {response.status_code} (expected {expected})")
    return response


def login(username: str) -> dict:
    r = client.post("/auth/login", data={"username": username, "password": "password123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


try:
    bob, carol = login("bob_agent"), login("carol_approver")
except httpx.ConnectError:
    sys.exit("Cannot reach the server. Start it first:  uvicorn app.main:app --reload")

print("\n--- 1. An agent tries to skip approval ---")
check("bob cancels a subscription directly", client.post("/subscriptions/sub_1/cancel", headers=bob), 428)

print("\n--- 2. Submit a plan ---")
plan = {
    "endpoint": "/subscriptions/{subscription_id}/cancel", "method": "POST",
    "parameters": {"subscription_id": "sub_1"}, "reason": "customer asked to cancel",
    "expected_result": "subscription cancelled", "risk_tier": "high_risk_write",
    "requires_approval": True, "requested_by": "bob_agent",
}
r = check("bob submits the plan", client.post("/plans", json=plan, headers=bob), 201)
plan_id = r.json()["plan_id"]
print(f"      plan_id = {plan_id}, status = {r.json()['status']}")

print("\n--- 3. Nothing happens until it is approved ---")
use = {"X-Plan-Id": plan_id}
check("bob tries to use the still-pending plan", client.post("/subscriptions/sub_1/cancel", headers={**bob, **use}), 409)
check("bob tries to approve it himself", client.post(f"/approvals/{plan_id}/approve", headers=bob), 403)

print("\n--- 4. An approver decides ---")
check("carol sees it in her queue", client.get("/approvals", headers=carol), 200)
r = check("carol approves", client.post(f"/approvals/{plan_id}/approve", json={"note": "verified with customer"}, headers=carol), 200)

print("\n--- 5. Execute, with a safe retry ---")
key = {"Idempotency-Key": f"demo-{uuid.uuid4()}"}
r1 = check("bob executes the approved plan", client.post("/subscriptions/sub_1/cancel", headers={**bob, **use, **key}), 200)
print(f"      result: {r1.json()}")
r2 = check("bob's network retries (same Idempotency-Key)", client.post("/subscriptions/sub_1/cancel", headers={**bob, **use, **key}), 200)
print(f"      replayed from the first result: {r2.headers.get('idempotent-replay') == 'true'}")
check("a NEW attempt with no key is refused (plan is single-use)", client.post("/subscriptions/sub_1/cancel", headers={**bob, **use}), 409)

print("\n--- 6. The audit trail ---")
events = check("carol reads the audit log", client.get("/audit", params={"plan_id": plan_id}, headers=carol), 200).json()["events"]
for e in events:
    print(f"      {e['timestamp'][11:19]}  {e['event_type']:20} by {e['actor']:15} {e['detail'][:50]}")

print("\n" + ("ALL CHECKS PASSED" if failures == 0 else f"{failures} CHECK(S) FAILED"))
sys.exit(1 if failures else 0)
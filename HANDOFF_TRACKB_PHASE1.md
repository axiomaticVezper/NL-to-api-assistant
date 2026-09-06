# Handoff — Track B, Phase 1 (in progress)

**From:** Track B
**Status:** In progress

## Contract fix
Resolved the role-permission ambiguity you flagged — `docs/PHASE0_CONTRACT.md`
now explicitly lists `agent` as allowed `high_risk_write` (cannot self-approve).
Your RBAC implementation was correct as built, no code change needed on your end.

## What's live on Track B
- `stubs/risk_tiers.json` — Track B-owned mapping of `METHOD /path` → risk tier,
  since the live OpenAPI schema has no risk-tier info in it. This is joined
  against your `openapi.json` at parse time (see `app_brain/schema_parser.py`).
  If you'd rather expose `x-risk-tier` as an OpenAPI extension on your routes
  later, I can drop this file and switch sources — no changes needed elsewhere
  in my pipeline either way.
- `app_brain/schema_parser.py` — parses your live schema + the risk tier
  mapping into typed `Endpoint` objects. Confirmed all 13 business endpoints
  resolve correctly against your running server.

## What I needed from your API to get this far
- Ran your server locally via `uvicorn app.main:app --reload` after adding
  a missing `app/requirements.txt` (wasn't committed — worth adding
  `pip freeze > app/requirements.txt` as a habit alongside code commits).
- Fetched `http://127.0.0.1:8000/openapi.json` to build the parser against
  your real schema instead of the earlier hand-written stub.

## Next on Track B
Candidate-endpoint retrieval / selection logic, then the LLM planning step.
# Handoff — Track B, Phase 1 (complete)

**From:** Track B
**Status:** Complete, tested manually against live Track A API

## Setup
```powershell
pip install -r app_brain/requirements.txt
```
Requires `GEMINI_API_KEY` in a local `.env` (gitignored, not committed — get your own key at
https://aistudio.google.com/apikey).

## What's live
- `app_brain/schema_parser.py` — parses OpenAPI schema + risk tier mapping into typed `Endpoint` objects
- `app_brain/retriever.py` — keyword-overlap candidate endpoint selection (naive — will need
  upgrading to embeddings once we have 30+ endpoints; fine for now)
- `app_brain/planner.py` — Gemini-based LLM planner producing validated `Plan` objects
  - Uses `gemini-flash-latest` (self-updating alias, avoids future model deprecations)
  - Known Gemini structured-output quirk: schema-less "object" params always return `{}` —
    worked around by using list[{name, value}] and converting to dict after parsing
  - Also normalizes cases where the model merges HTTP method into the endpoint string
- `app_brain/validator.py` — validates a Plan's endpoint/params/risk_tier against ground
  truth from the schema before it would be sent to your API

## Try it yourself
With your server running (`uvicorn app.main:app --reload`):
```powershell
python -m app_brain.validator
```
This runs schema parsing → retrieval → planning → validation end to end on a sample request
and prints the resulting `Plan`.

## Depends on
- `stubs/risk_tiers.json` — my own mapping of endpoint → risk tier, since your OpenAPI schema
  has no risk-tier info in it. If you'd rather add `x-risk-tier` as an OpenAPI extension on
  your routes, I can drop this file and switch sources with no changes anywhere else in my code.
- `openapi_live.json` — not committed; regenerate locally by hitting
  `http://127.0.0.1:8000/openapi.json` while your server runs.

## Known limitations (Phase 2+ work)
- Only tested against single-step requests so far — no multi-step workflow chaining yet
- No retry logic around Gemini calls (transient 503s happen on the free tier)
- Retriever is keyword-based, not semantic — fine for 13 endpoints, will need revisiting later

## Next on Track B (Phase 2)
Approval workflow integration, dry-run mode, multi-step workflow orchestration
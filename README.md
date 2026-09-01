# NL to API Assistant

Natural Language to API Assistant — governed, self-correcting agentic execution over a mock business API.

## Status
Phase 0 (Shared Contract) is complete. See `docs/PHASE0_CONTRACT.md` for the agreed domain, endpoints, and roles.
The shared data contracts live in `contracts/` as Pydantic models: `Plan`, `WorkflowState`, `AuditEvent`.

## Setup
\`\`\`powershell
git clone https://github.com/axiomaticVezper/nl-to-api-assistant.git
cd nl-to-api-assistant
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Mac/Linux
pip install -r contracts/requirements.txt
\`\`\`

## Project structure
- `contracts/` — shared Pydantic schemas both tracks import (Plan, WorkflowState, AuditEvent)
- `docs/PHASE0_CONTRACT.md` — the agreed domain, endpoints, and roles from Phase 0

## Tracks
- **Track A — "The System":** mock API, auth/RBAC, approval workflow, audit, idempotency, rollback, observability
- **Track B — "The Brain":** LLM planning, validation, dry-run, workflow orchestration, self-correction, UI

Currently: Sahil is on Track B, partner is starting Track A.

## Handoffs
When swapping tracks or ending a session, write a note as `HANDOFF_<track>_<phase>.md` in the repo root.
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid

from contracts.plan import RiskTier

class EventType(str, Enum):
    plan_created = "plan_created"
    validated = "validated"
    validation_failed = "validation_failed"
    approval_requested = "approval_requested"
    approved = "approved"
    rejected = "rejected"
    executed = "executed"
    execution_failed = "execution_failed"
    rolled_back = "rolled_back"

class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: str                        # links back to the Plan this event is about
    workflow_id: str | None = None      # set if part of a multi-step workflow
    event_type: EventType
    actor: str                          # who/what caused this event (user id, "system", or approver id)
    endpoint: str
    risk_tier: RiskTier
    detail: str                         # human-readable detail, e.g. rejection reason, error message
    timestamp: datetime = Field(default_factory=datetime.utcnow)
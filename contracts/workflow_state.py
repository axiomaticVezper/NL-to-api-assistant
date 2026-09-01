from pydantic import BaseModel, Field
from enum import Enum
from typing import Any
import uuid

from contracts.plan import Plan

class StepStatus(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    rolled_back = "rolled_back"

class WorkflowStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plan: Plan
    output: dict[str, Any] | None = None
    status: StepStatus = StepStatus.pending

class WorkflowStatus(str, Enum):
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    rolled_back = "rolled_back"

class WorkflowState(BaseModel):
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_request: str
    steps: list[WorkflowStep]
    status: WorkflowStatus = WorkflowStatus.in_progress
    requested_by: str
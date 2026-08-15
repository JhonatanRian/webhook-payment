from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class SchedulerMode(StrEnum):
    ONCE = "once"
    RECURRING = "recurring"


class TriggerType(StrEnum):
    SCHEDULED = "scheduled"
    MANUAL = "manual"


class CycleStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class SchedulerStatusResponse(BaseModel):
    scheduled_cycles_completed: int = Field(
        ..., description="Completed scheduled automatic cycles in the system"
    )
    manual_triggers_completed: int = Field(
        ..., description="Completed manual cycles triggered via API"
    )
    max_cycles: int = Field(..., description="Maximum scheduled cycles allowed per round/window")
    interval_minutes: int = Field(
        ..., description="Configured interval between cycles in minutes (e.g. 180)"
    )
    remaining_cycles: int = Field(..., description="Remaining scheduled cycles in current mode")
    mode: SchedulerMode = Field(..., description="Scheduler operating mode: 'once' or 'recurring'")
    is_running: bool = Field(..., description="Indicates whether APScheduler is actively running")
    next_run_time: datetime | None = Field(
        None, description="ISO timestamp in UTC of next scheduled cycle execution"
    )


class SchedulerModeUpdateRequest(BaseModel):
    mode: SchedulerMode = Field(
        ..., description="Target scheduler operating mode: 'once' or 'recurring'"
    )


class SchedulerControlResponse(BaseModel):
    message: str = Field(..., description="Descriptive outcome message of the executed action")
    mode: SchedulerMode | None = Field(None, description="Active operating mode after the action")

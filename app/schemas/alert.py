from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AlertSeverity = Literal["CRITICAL", "WARNING", "INFO"]

ALERT_SEVERITIES = frozenset({"CRITICAL", "WARNING", "INFO"})


class AlertCreate(BaseModel):
    pipeline_id: int = Field(..., gt=0)
    severity: AlertSeverity
    message: str = Field(..., min_length=1)

    @field_validator("severity", mode="before")
    @classmethod
    def normalize_severity(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in ALERT_SEVERITIES:
            raise ValueError(
                f"severity must be one of: {', '.join(sorted(ALERT_SEVERITIES))}"
            )
        return normalized


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pipeline_id: int
    severity: AlertSeverity
    message: str
    created_at: datetime

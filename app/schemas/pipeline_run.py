from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PipelineRunCreate(BaseModel):
    pipeline_id: int = Field(..., gt=0)
    status: str = Field(..., min_length=1, max_length=50)
    duration_seconds: float | None = Field(None, ge=0)
    error_message: str | None = None


class PipelineRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pipeline_id: int
    status: str
    duration_seconds: float | None
    error_message: str | None
    run_timestamp: datetime

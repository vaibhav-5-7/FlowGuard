from datetime import datetime

from pydantic import BaseModel, Field


class PipelineHealthResponse(BaseModel):
    pipeline_id: int
    total_runs: int = Field(..., ge=0)
    successful_runs: int = Field(..., ge=0)
    failed_runs: int = Field(..., ge=0)
    success_rate: float = Field(..., ge=0, le=100)
    avg_duration_seconds: float = Field(..., ge=0)
    last_run_status: str | None = None
    last_run_timestamp: datetime | None = None

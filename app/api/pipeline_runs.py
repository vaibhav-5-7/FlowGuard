from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.pipeline import Pipeline, PipelineRun
from app.schemas.pipeline_run import PipelineRunCreate, PipelineRunResponse

router = APIRouter(prefix="/pipeline-runs", tags=["pipeline-runs"])


@router.post("", response_model=PipelineRunResponse, status_code=201)
def create_pipeline_run(
    payload: PipelineRunCreate,
    db: Annotated[Session, Depends(get_db)],
) -> PipelineRun:
    pipeline = db.query(Pipeline).filter(Pipeline.id == payload.pipeline_id).first()
    if pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    run = PipelineRun(
        pipeline_id=payload.pipeline_id,
        status=payload.status,
        duration_seconds=payload.duration_seconds,
        error_message=payload.error_message,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.get("", response_model=list[PipelineRunResponse])
def list_pipeline_runs(
    db: Annotated[Session, Depends(get_db)],
) -> list[PipelineRun]:
    return (
        db.query(PipelineRun)
        .order_by(PipelineRun.run_timestamp.desc())
        .all()
    )


@router.get("/{pipeline_id}", response_model=list[PipelineRunResponse])
def list_pipeline_runs_by_pipeline(
    pipeline_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> list[PipelineRun]:
    return (
        db.query(PipelineRun)
        .filter(PipelineRun.pipeline_id == pipeline_id)
        .order_by(PipelineRun.run_timestamp.desc())
        .all()
    )

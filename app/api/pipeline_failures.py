from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.pipeline import PipelineRun

router = APIRouter(prefix="/pipeline-failures", tags=["pipeline-failures"])


@router.get("")
def get_pipeline_failures(
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, int]:
    rows = (
        db.query(PipelineRun.error_message, func.count(PipelineRun.id))
        .filter(PipelineRun.error_message.isnot(None))
        .group_by(PipelineRun.error_message)
        .order_by(func.count(PipelineRun.id).desc())
        .all()
    )
    return {error_message: count for error_message, count in rows}

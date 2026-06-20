from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.pipeline import Pipeline
from app.schemas.pipeline import PipelineCreate, PipelineResponse

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


@router.post("", response_model=PipelineResponse, status_code=201)
def create_pipeline(
    payload: PipelineCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Pipeline:
    pipeline = Pipeline(name=payload.name, description=payload.description)
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)
    return pipeline


@router.get("", response_model=list[PipelineResponse])
def list_pipelines(
    db: Annotated[Session, Depends(get_db)],
) -> list[Pipeline]:
    return db.query(Pipeline).order_by(Pipeline.created_at.desc()).all()

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.alert import Alert
from app.schemas.alert import AlertCreate, AlertResponse

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("", response_model=AlertResponse, status_code=201)
def create_alert(
    payload: AlertCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Alert:
    alert = Alert(
        pipeline_id=payload.pipeline_id,
        severity=payload.severity,
        message=payload.message,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.get("", response_model=list[AlertResponse])
def list_alerts(
    db: Annotated[Session, Depends(get_db)],
) -> list[Alert]:
    return db.query(Alert).order_by(Alert.created_at.desc()).all()


@router.get("/{pipeline_id}", response_model=list[AlertResponse])
def list_alerts_by_pipeline(
    pipeline_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> list[Alert]:
    return (
        db.query(Alert)
        .filter(Alert.pipeline_id == pipeline_id)
        .order_by(Alert.created_at.desc())
        .all()
    )

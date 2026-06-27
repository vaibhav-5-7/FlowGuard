from contextlib import asynccontextmanager
from typing import Any


from fastapi import FastAPI

from app.api.alerts import router as alerts_router
from app.api.auth import router as auth_router
from app.api.pipeline_failures import router as pipeline_failures_router
from app.api.pipeline_health import router as pipeline_health_router
from app.api.pipeline_runs import router as pipeline_runs_router
from app.api.pipelines import router as pipelines_router
from app.db.database import create_tables

OPENAPI_TAGS = [
    {
        "name": "pipelines",
        "description": "Create and list data pipelines.",
    },
    {
        "name": "pipeline-runs",
        "description": "Track pipeline execution runs, including status, duration, and errors.",
    },
    {
        "name": "pipeline-health",
        "description": "Aggregate health metrics for pipelines based on run history.",
    },
    {
        "name": "pipeline-failures",
        "description": "Aggregate failure counts by error message across pipeline runs.",
    },
    {
        "name": "alerts",
        "description": "Manage pipeline alerts including creation and listing.",
    },
]


@asynccontextmanager
async def lifespan(_: FastAPI) -> Any:
    create_tables()
    yield


app = FastAPI(
    title="FlowGuard",
    version="0.1.0",
    description="API for managing data pipelines and tracking pipeline run history.",
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
)

app.include_router(auth_router)

app.include_router(pipelines_router)
app.include_router(pipeline_runs_router)
app.include_router(pipeline_health_router)
app.include_router(pipeline_failures_router)
app.include_router(alerts_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "FlowGuard API Running"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}

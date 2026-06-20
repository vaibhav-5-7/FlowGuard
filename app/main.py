from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from app.api.pipelines import router as pipelines_router
from app.db.database import create_tables


@asynccontextmanager
async def lifespan(_: FastAPI) -> Any:
    create_tables()
    yield


app = FastAPI(title="FlowGuard", version="0.1.0", lifespan=lifespan)

app.include_router(pipelines_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "FlowGuard API Running"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}

"""Application factory: health and OpenAPI only, without business endpoints."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import Settings
from app.db.database import Database


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    database = Database(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        database.close()

    application = FastAPI(
        title="WagaMaga AI API",
        version="0.1.0",
        description="M0 foundation. No farm, identity, advisory or planning features yet.",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
        openapi_url="/openapi.json" if settings.app_env != "production" else None,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Content-Type"],
    )
    application.state.database = database

    @application.get("/health/live", tags=["Health"])
    def liveness() -> dict[str, str]:
        return {"status": "ok", "service": "wagamaga-api"}

    @application.get(
        "/health/ready", tags=["Health"], responses={503: {"description": "Not ready"}}
    )
    def readiness() -> JSONResponse:
        result = database.check_ready()
        return JSONResponse(result.payload(), status_code=200 if result.status == "ready" else 503)

    return application


app = create_app()

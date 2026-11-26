"""Application factory with health, accounts, private Farm Records and website support."""

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.db.database import Database
from app.modules.advisory.routes import review_router
from app.modules.advisory.routes import router as advisor_router
from app.modules.farms.routes import router as farms_router
from app.modules.identity.routes import router as identity_router
from app.modules.identity.security import COOKIE_NAME, COOKIE_PATH, IdentityError
from app.modules.knowledge.pdf_text import MAX_BYTES as PDF_MAX_BYTES
from app.modules.knowledge.routes import PDF_UPLOAD_PATH
from app.modules.knowledge.routes import advisor_router as knowledge_advisor_router
from app.modules.knowledge.routes import evaluation_router as knowledge_evaluation_router
from app.modules.knowledge.routes import farmer_router as knowledge_farmer_router
from app.modules.knowledge.routes import router as knowledge_router
from app.modules.notifications.routes import router as notifications_router
from app.modules.reporting.routes import router as reporting_router
from app.modules.support.routes import router as support_router


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
        description=(
            "Accounts, audit, notifications, owner-only Farm Records, website support and health. "
            "Weekly planning, assigned advisor review, weather and cited chilli knowledge."
        ),
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
        openapi_url="/openapi.json" if settings.app_env != "production" else None,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-WagaMaga-Client", "Idempotency-Key"],
    )
    application.state.database = database
    application.state.settings = settings

    def error_response(request: Request, status: int, code: str, message: str, **extra):
        return JSONResponse(
            {
                "code": code,
                "message": message,
                "request_id": getattr(request.state, "request_id", str(uuid4())),
                "field_errors": [],
                "retryable": status in {429, 503},
                **extra,
            },
            status_code=status,
            headers={"Cache-Control": "no-store"},
        )

    @application.middleware("http")
    async def private_responses(request: Request, call_next):
        request.state.request_id = str(uuid4())
        if request.url.path.startswith("/api/v1"):
            size = request.headers.get("content-length", "0")
            limit = (
                PDF_MAX_BYTES
                if request.method == "POST" and request.url.path == PDF_UPLOAD_PATH
                else 16384
            )
            if not size.isascii() or not size.isdecimal() or len(size) > 8 or int(size) > limit:
                return error_response(
                    request, 413, "REQUEST_TOO_LARGE", "The request is too large."
                )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        if request.url.path.startswith("/api/v1"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(IdentityError)
    async def identity_error(request: Request, error: IdentityError):
        response = error_response(request, error.status, error.code, error.message)
        if error.status == 401:
            response.headers["WWW-Authenticate"] = "Bearer"
        if error.retry_after is not None:
            response.headers["Retry-After"] = str(error.retry_after)
        if error.clear_cookie:
            response.delete_cookie(COOKIE_NAME, path=COOKIE_PATH)
        return response

    @application.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, error: RequestValidationError):
        # Pydantic's raw input/ctx can contain plaintext passwords. Return field names only.
        fields = [
            {
                "field": ".".join(str(part) for part in item["loc"]),
                "message": "Check this field's format, length and allowed values.",
            }
            for item in error.errors()
        ]
        return error_response(
            request, 422, "VALIDATION_ERROR", "Check the form fields.", field_errors=fields
        )

    @application.exception_handler(SQLAlchemyError)
    async def unavailable(request: Request, error: SQLAlchemyError):
        return error_response(
            request, 503, "DATABASE_UNAVAILABLE", "Data access is temporarily unavailable."
        )

    application.include_router(identity_router)
    application.include_router(notifications_router)
    application.include_router(farms_router)
    application.include_router(advisor_router)
    application.include_router(review_router)
    application.include_router(support_router)
    application.include_router(reporting_router)
    application.include_router(knowledge_router)
    application.include_router(knowledge_evaluation_router)
    application.include_router(knowledge_farmer_router)
    application.include_router(knowledge_advisor_router)

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

"""Twemp FastAPI application factory."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.dependencies import SettingsDep
from app.api.routes import router as workflow_router
from app.config import get_settings

logger = logging.getLogger("twemp")


def _error_body(message: str, details: list[str] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"error": message}
    if details:
        body["details"] = details
    return body


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Twemp incident workflow API",
        description=(
            "Hierarchical multi-agent incident response with a mandatory human approval gate."
        ),
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        max_age=600,
    )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            f"{'.'.join(str(part) for part in error['loc'][1:])}: {error['msg']}"
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error_body("Request validation failed", details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error while serving a workflow request", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("The workflow request could not be completed"),
        )

    @app.get("/health", tags=["system"], summary="Liveness and provider-mode probe")
    async def health(settings: SettingsDep) -> dict[str, str]:
        return {"status": "ok", "provider": settings.agent_provider}

    app.include_router(workflow_router)
    return app


app = create_app()

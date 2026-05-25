import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.health import router as health_router
from app.api.v1.router import router as api_v1_router
from app.logging import configure_logging
from app.middleware.logging import log_api_request_middleware
from app.schemas.common import ErrorDetail, ResponseBuilder
from config.settings import get_settings

settings = get_settings()
configure_logging(settings)
logger = logging.getLogger(__name__)
app = FastAPI(title=settings.app_name)

if settings.log_api_requests:
    app.middleware("http")(log_api_request_middleware)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    _request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    response = ResponseBuilder.error(
        message=message,
        errors=[ErrorDetail(code="http_error", detail=message)],
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(mode="json"),
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = [
        ErrorDetail(
            code="validation_error",
            detail=error["msg"],
            field=".".join(str(part) for part in error["loc"]),
        )
        for error in exc.errors()
    ]
    response = ResponseBuilder.error(
        message="Validation failed.",
        errors=errors,
    )
    return JSONResponse(
        status_code=400,
        content=response.model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception("Unhandled exception while processing %s", request.url.path)
    message = "Internal server error."
    response = ResponseBuilder.error(
        message=message,
        errors=[ErrorDetail(code="internal_server_error", detail=message)],
    )
    return JSONResponse(
        status_code=500,
        content=response.model_dump(mode="json"),
    )


app.include_router(health_router)
app.include_router(api_v1_router)


def custom_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    for path_item in openapi_schema.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses", {})
            validation_response = responses.pop("422", None)
            if validation_response is not None and "400" not in responses:
                responses["400"] = validation_response

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


def main() -> None:
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_reload,
    )


if __name__ == "__main__":
    main()

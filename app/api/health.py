from __future__ import annotations

from fastapi import APIRouter, status

from app.schemas.common import ApiResponse, ResponseBuilder

router = APIRouter(tags=["health"])


@router.get(
    "/",
    response_model=ApiResponse[dict[str, str]],
    status_code=status.HTTP_200_OK,
)
def read_root() -> ApiResponse[dict[str, str]]:
    return ResponseBuilder.success(
        {"message": "backend-eng-assignment is running"},
        message="Application is running.",
    )


@router.get(
    "/health",
    response_model=ApiResponse[dict[str, str]],
    status_code=status.HTTP_200_OK,
)
def health_check() -> ApiResponse[dict[str, str]]:
    return ResponseBuilder.success(
        {"status": "ok"},
        message="Health check passed.",
    )

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    detail: str
    field: str | None = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: T | None = None
    errors: list[ErrorDetail] = Field(default_factory=list)


class ResponseBuilder:
    @staticmethod
    def success(data: T, message: str = "Request successful.") -> ApiResponse[T]:
        return ApiResponse[T](success=True, message=message, data=data, errors=[])

    @staticmethod
    def created(
        data: T, message: str = "Resource created successfully."
    ) -> ApiResponse[T]:
        return ApiResponse[T](success=True, message=message, data=data, errors=[])

    @staticmethod
    def error(
        message: str,
        *,
        errors: list[ErrorDetail] | None = None,
    ) -> ApiResponse[None]:
        return ApiResponse[None](
            success=False,
            message=message,
            data=None,
            errors=errors or [],
        )

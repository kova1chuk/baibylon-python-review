from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class HealthResponse(BaseModel):
    status: str
    message: str
    version: str


class ErrorResponse(BaseModel):
    error: str


class SuccessResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None = None

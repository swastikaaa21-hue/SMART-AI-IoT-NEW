"""
Custom application exceptions with HTTP status codes.
"""

from __future__ import annotations

from fastapi import HTTPException, status


class NotFoundError(HTTPException):
    def __init__(self, resource: str, identifier: str | None = None):
        detail = f"{resource} not found"
        if identifier:
            detail = f"{resource} '{identifier}' not found"
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class AlreadyExistsError(HTTPException):
    def __init__(self, resource: str, identifier: str | None = None):
        detail = f"{resource} already exists"
        if identifier:
            detail = f"{resource} '{identifier}' already exists"
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class UnauthorizedError(HTTPException):
    def __init__(self, detail: str = "Invalid or expired credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenError(HTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class BadRequestError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ServiceUnavailableError(HTTPException):
    def __init__(self, service: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{service} is currently unavailable",
        )


class MQTTPublishError(HTTPException):
    def __init__(self, device_id: str):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to publish MQTT command to device '{device_id}'",
        )

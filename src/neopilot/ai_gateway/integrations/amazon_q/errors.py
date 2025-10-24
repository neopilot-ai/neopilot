from enum import StrEnum
from functools import wraps
from typing import Optional

import botocore
from fastapi import HTTPException, status

from neopilot.ai_gateway.tracking import log_exception

__all__ = [
    "AccessDeniedExceptionReason",
    "AWSException",
    "raise_aws_errors",
]


class AccessDeniedExceptionReason(StrEnum):
    GITLAB_EXPIRED_IDENTITY = "gitLabExpiredIdentity"
    GITLAB_INVALID_IDENTITY = "gitLabInvalidIdentity"
    OTHER = "other"


class AWSException(Exception):
    """Base exception for AWS errors."""

    def __init__(
        self,
        response_code: Optional[int],
        error_code: str,
        error_message: str,
        exception_str: str,
    ):
        self.response_code = response_code
        self.error_code = error_code
        self.error_message = error_message
        self.exception_str = exception_str
        super().__init__(exception_str)

    def __str__(self):
        return f"AWSException: {self.error_code} - {self.error_message} (HTTP {self.response_code})"

    def is_conflict(self):
        return self.error_code == "ConflictException"

    def is_not_found(self):
        return self.error_code == "ResourceNotFoundException"

    def to_http_exception(self):
        if str(self.error_code) in (
            "ResourceNotFoundException",
            "UnknownOperationException",
            "404",
        ):
            return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=self.exception_str)
        if str(self.error_code) in ("AccessDeniedException", "403"):
            return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=self.exception_str)
        if str(self.error_code) in ("ValidationException", "400"):
            return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=self.exception_str)
        if str(self.error_code) in ("ThrottlingException", "429"):
            return HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=self.exception_str)

        # For any other AWS errors, return a 500 Internal Server Error
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AWS Error: {self.exception_str}",
        )

    @classmethod
    def from_exception(cls, e: botocore.exceptions.ClientError):
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        response_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        response_metadata = e.response.get("ResponseMetadata")

        if response_metadata:
            response_code = response_metadata.get("HTTPStatusCode")

        return cls(
            response_code=response_code,
            error_code=error_code,
            error_message=error_message,
            exception_str=str(e),
        )


def raise_aws_errors(func):
    """Decorator that translates an AWS error to a user-visible HTTPS status code."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except botocore.exceptions.ParamValidationError as e:
            log_exception(e)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except botocore.exceptions.ClientError as e:
            aws_error = AWSException.from_exception(e)

            log_exception(
                e,
                aws_error_code=aws_error.error_code,
                aws_error_message=aws_error.error_message,
                aws_http_response_code=aws_error.response_code,
            )
            raise aws_error

    return wrapper

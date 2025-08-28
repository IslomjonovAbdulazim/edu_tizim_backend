from typing import Optional
from fastapi import HTTPException

class CustomHTTPException(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str,
        headers: Optional[dict] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code

# Authentication & Authorization Exceptions
class AuthenticationException(CustomHTTPException):
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=401,
            detail=detail,
            error_code="AUTH_FAILED"
        )

class InsufficientPermissionsException(CustomHTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=403,
            detail=detail,
            error_code="INSUFFICIENT_PERMISSIONS"
        )

class InvalidRoleException(CustomHTTPException):
    def __init__(self, detail: str = "Invalid role for this operation"):
        super().__init__(
            status_code=403,
            detail=detail,
            error_code="INVALID_ROLE"
        )

# Resource Exceptions
class ResourceNotFoundException(CustomHTTPException):
    def __init__(self, resource: str, detail: Optional[str] = None):
        detail = detail or f"{resource} not found"
        super().__init__(
            status_code=404,
            detail=detail,
            error_code="RESOURCE_NOT_FOUND"
        )

class ResourceAlreadyExistsException(CustomHTTPException):
    def __init__(self, resource: str, detail: Optional[str] = None):
        detail = detail or f"{resource} already exists"
        super().__init__(
            status_code=409,
            detail=detail,
            error_code="RESOURCE_EXISTS"
        )

# Validation Exceptions
class InvalidDataException(CustomHTTPException):
    def __init__(self, detail: str = "Invalid data provided"):
        super().__init__(
            status_code=422,
            detail=detail,
            error_code="INVALID_DATA"
        )

class ValidationException(CustomHTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=422,
            detail=detail,
            error_code="VALIDATION_ERROR"
        )

# Business Logic Exceptions
class StudentNotInGroupException(CustomHTTPException):
    def __init__(self, detail: str = "Student is not in this group"):
        super().__init__(
            status_code=400,
            detail=detail,
            error_code="STUDENT_NOT_IN_GROUP"
        )

class GroupCapacityExceededException(CustomHTTPException):
    def __init__(self, detail: str = "Group capacity exceeded"):
        super().__init__(
            status_code=400,
            detail=detail,
            error_code="GROUP_CAPACITY_EXCEEDED"
        )

class ProgressNotFoundException(CustomHTTPException):
    def __init__(self, detail: str = "Progress record not found"):
        super().__init__(
            status_code=404,
            detail=detail,
            error_code="PROGRESS_NOT_FOUND"
        )

# Parent-Student Relationship Exceptions
class ParentStudentRelationshipException(CustomHTTPException):
    def __init__(self, detail: str = "Invalid parent-student relationship"):
        super().__init__(
            status_code=400,
            detail=detail,
            error_code="INVALID_PARENT_STUDENT_RELATION"
        )

# File Upload Exceptions
class FileUploadException(CustomHTTPException):
    def __init__(self, detail: str = "File upload failed"):
        super().__init__(
            status_code=400,
            detail=detail,
            error_code="FILE_UPLOAD_FAILED"
        )

class UnsupportedFileTypeException(CustomHTTPException):
    def __init__(self, detail: str = "Unsupported file type"):
        super().__init__(
            status_code=400,
            detail=detail,
            error_code="UNSUPPORTED_FILE_TYPE"
        )

# Database Exceptions
class DatabaseException(CustomHTTPException):
    def __init__(self, detail: str = "Database operation failed"):
        super().__init__(
            status_code=500,
            detail=detail,
            error_code="DATABASE_ERROR"
        )
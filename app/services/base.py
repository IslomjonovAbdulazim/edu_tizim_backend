from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.repositories import RepositoryFactory


class BaseService:
    """Base service class with common functionality"""

    def __init__(self, db: Session):
        self.db = db
        self.repos = RepositoryFactory(db)

    def _validate_required_fields(self, data: Dict[str, Any], required_fields: list) -> Dict[str, str]:
        """Validate required fields and return error messages"""
        errors = {}
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                errors[field] = f"{field} is required"
        return errors

    def _check_permissions(self, user_id: int, required_roles: list, learning_center_id: Optional[int] = None) -> bool:
        """Check if user has required permissions"""
        user = self.repos.user.get(user_id)
        if not user or not user.is_active:
            return False

        # Check role
        if not user.has_any_role(required_roles):
            return False

        # Check learning center access if specified
        if learning_center_id and user.learning_center_id != learning_center_id:
            return False

        return True

    def _format_error_response(self, message: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Format error response"""
        response = {"success": False, "message": message}
        if details:
            response["details"] = details
        return response

    def _format_success_response(self, data: Any = None, message: str = "Success") -> Dict[str, Any]:
        """Format success response"""
        response = {"success": True, "message": message}
        if data is not None:
            response["data"] = data
        return response
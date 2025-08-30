from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.repositories import RepositoryFactory
from app.models.user import UserRole


class BaseService:
    """Base service class with common functionality and repository access"""

    def __init__(self, db: Session):
        self.db = db
        self.repos = RepositoryFactory(db)

    def _format_success_response(self, data: Any = None, message: str = "Operation successful") -> Dict[str, Any]:
        """Format standard success response"""
        return {
            "success": True,
            "message": message,
            "data": data
        }

    def _format_error_response(self, message: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Format standard error response"""
        response = {
            "success": False,
            "message": message,
            "data": None
        }
        if details:
            response["details"] = details
        return response

    def _check_permissions(
            self,
            user_id: int,
            required_roles: list,
            learning_center_id: Optional[int] = None
    ) -> bool:
        """Check if user has required permissions"""
        user = self.repos.user.get(user_id)
        if not user or not user.is_active:
            return False

        # Super admin can do everything
        if any(role.role == UserRole.SUPER_ADMIN for role in user.center_roles if role.is_active):
            return True

        # Check roles in specific learning center
        if learning_center_id:
            user_roles = [
                role.role for role in user.center_roles
                if role.learning_center_id == learning_center_id and role.is_active
            ]
            return any(role in required_roles for role in user_roles)

        # Check roles across all centers (for general permissions)
        user_roles = [role.role for role in user.center_roles if role.is_active]
        return any(role in required_roles for role in user_roles)

    def _get_user_learning_center(self, user_id: int) -> Optional[int]:
        """Get user's learning center ID (first active one)"""
        user = self.repos.user.get(user_id)
        if not user:
            return None

        active_roles = [role for role in user.center_roles if role.is_active]
        return active_roles[0].learning_center_id if active_roles else None

    def _validate_learning_center_access(self, user_id: int, learning_center_id: int) -> bool:
        """Validate user has access to learning center"""
        user = self.repos.user.get(user_id)
        if not user:
            return False

        # Super admin has access to all centers
        if any(role.role == UserRole.SUPER_ADMIN for role in user.center_roles if role.is_active):
            return True

        # Check if user has role in this learning center
        return any(
            role.learning_center_id == learning_center_id and role.is_active
            for role in user.center_roles
        )

    def _check_center_active(self, learning_center_id: int) -> bool:
        """Check if learning center is active"""
        center = self.repos.learning_center.get(learning_center_id)
        return center and center.is_active

    def _commit_or_rollback(self, success: bool):
        """Commit transaction on success, rollback on failure"""
        if success:
            self.db.commit()
        else:
            self.db.rollback()
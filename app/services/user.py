from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.user import UserRole
from app.schemas.user import UserCreate, UserUpdate, UserResponse, LoginRequest
from app.services.base import BaseService


class UserService(BaseService):
    """User service for authentication and user management"""

    def __init__(self, db: Session):
        super().__init__(db)

    def create_user(self, user_data: UserCreate, creator_id: Optional[int] = None) -> Dict[str, Any]:
        """Create new user with role assignment"""
        # Validate creator permissions if provided
        if creator_id and not self._check_permissions(
            creator_id,
            [UserRole.RECEPTION, UserRole.ADMIN, UserRole.SUPER_ADMIN],
            user_data.learning_center_id
        ):
            return self._format_error_response("Insufficient permissions to create users")

        # Check if telegram ID already exists
        if user_data.telegram_id and self.repos.user.telegram_id_exists(user_data.telegram_id):
            return self._format_error_response("Telegram ID already registered")

        # Check if phone exists in learning center
        if self.repos.user.phone_exists_in_center(user_data.phone_number, user_data.learning_center_id):
            return self._format_error_response("Phone number already registered in this learning center")

        # Verify learning center is active
        if not self._check_center_active(user_data.learning_center_id):
            return self._format_error_response("Learning center is not active")

        try:
            # Create user with role
            user = self.repos.user.create_user_with_role(
                user_data.dict(exclude={'role'}),
                user_data.learning_center_id,
                user_data.role
            )

            return self._format_success_response(
                UserResponse.from_orm(user),
                "User created successfully"
            )

        except Exception as e:
            return self._format_error_response(f"Failed to create user: {str(e)}")

    def authenticate_user(self, login_data: LoginRequest) -> Dict[str, Any]:
        """Authenticate user by phone and learning center"""
        user = self.repos.user.get_by_phone_and_center(
            login_data.phone_number,
            login_data.learning_center_id
        )

        if not user:
            return self._format_error_response("User not found in this learning center")

        if not user.is_active:
            return self._format_error_response("User account is deactivated")

        # Check learning center status
        if not self._check_center_active(login_data.learning_center_id):
            return self._format_error_response("Learning center subscription expired")

        return self._format_success_response({
            "user": UserResponse.from_orm(user),
            "verification_required": not user.is_verified,
            "next_step": "verify_phone" if not user.is_verified else "access_dashboard"
        })

    def get_user(self, user_id: int, requester_id: int) -> Dict[str, Any]:
        """Get user details with permission check"""
        user = self.repos.user.get(user_id)
        if not user:
            return self._format_error_response("User not found")

        # Permission check: self, admin, or same learning center staff
        can_view = (
            user_id == requester_id or
            self._check_permissions(requester_id, [UserRole.ADMIN, UserRole.SUPER_ADMIN]) or
            (self._check_permissions(requester_id, [UserRole.RECEPTION, UserRole.GROUP_MANAGER]) and
             self._validate_learning_center_access(requester_id, self._get_user_learning_center(user_id)))
        )

        if not can_view:
            return self._format_error_response("Insufficient permissions")

        return self._format_success_response(UserResponse.from_orm(user))

    def update_user(self, user_id: int, update_data: UserUpdate, updater_id: int) -> Dict[str, Any]:
        """Update user information"""
        user = self.repos.user.get(user_id)
        if not user:
            return self._format_error_response("User not found")

        # Permission check
        can_update = (
            user_id == updater_id or  # Self update
            self._check_permissions(updater_id, [UserRole.ADMIN, UserRole.SUPER_ADMIN]) or
            (self._check_permissions(updater_id, [UserRole.RECEPTION]) and
             self._validate_learning_center_access(updater_id, self._get_user_learning_center(user_id)))
        )

        if not can_update:
            return self._format_error_response("Insufficient permissions")

        try:
            updated_user = self.repos.user.update(user_id, update_data.dict(exclude_unset=True))
            return self._format_success_response(
                UserResponse.from_orm(updated_user),
                "User updated successfully"
            )

        except Exception as e:
            return self._format_error_response(f"Failed to update user: {str(e)}")

    def change_user_role(self, user_id: int, new_role: UserRole, changer_id: int) -> Dict[str, Any]:
        """Change user role with permission validation"""
        if not self._check_permissions(changer_id, [UserRole.ADMIN, UserRole.SUPER_ADMIN]):
            return self._format_error_response("Only admins can change user roles")

        user = self.repos.user.get(user_id)
        if not user:
            return self._format_error_response("User not found")

        # Additional restrictions for non-super-admins
        changer = self.repos.user.get(changer_id)
        is_super_admin = any(
            role.role == UserRole.SUPER_ADMIN
            for role in changer.center_roles
            if role.is_active
        )

        if not is_super_admin:
            # Regular admin can't create other admins or super admins
            if new_role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                return self._format_error_response("Cannot assign admin or super admin role")

            # Must be in same learning center
            user_center = self._get_user_learning_center(user_id)
            if not self._validate_learning_center_access(changer_id, user_center):
                return self._format_error_response("Can only change roles within same learning center")

        try:
            updated_user = self.repos.user.change_role(user_id, new_role)
            return self._format_success_response(
                UserResponse.from_orm(updated_user),
                f"User role changed to {new_role.value}"
            )

        except Exception as e:
            return self._format_error_response(f"Failed to change role: {str(e)}")

    def verify_user(self, user_id: int) -> Dict[str, Any]:
        """Mark user as verified (used by verification service)"""
        user = self.repos.user.verify_user(user_id)
        if not user:
            return self._format_error_response("User not found")

        return self._format_success_response(
            UserResponse.from_orm(user),
            "User verified successfully"
        )

    def get_users_by_center(self, learning_center_id: int, requester_id: int) -> Dict[str, Any]:
        """Get all users in learning center"""
        if not self._check_permissions(
            requester_id,
            [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.RECEPTION, UserRole.GROUP_MANAGER],
            learning_center_id
        ):
            return self._format_error_response("Insufficient permissions")

        users = self.repos.user.get_users_by_center(learning_center_id)
        users_data = [UserResponse.from_orm(user) for user in users]

        return self._format_success_response(users_data)

    def search_users(self, query: str, learning_center_id: int, requester_id: int) -> Dict[str, Any]:
        """Search users by name or phone"""
        if not self._check_permissions(
            requester_id,
            [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.RECEPTION, UserRole.GROUP_MANAGER],
            learning_center_id
        ):
            return self._format_error_response("Insufficient permissions")

        users = self.repos.user.search_users(learning_center_id, query)
        users_data = [UserResponse.from_orm(user) for user in users]

        return self._format_success_response(users_data)

    def deactivate_user(self, user_id: int, deactivator_id: int) -> Dict[str, Any]:
        """Deactivate user account"""
        if not self._check_permissions(deactivator_id, [UserRole.ADMIN, UserRole.SUPER_ADMIN]):
            return self._format_error_response("Admin access required")

        user = self.repos.user.get(user_id)
        if not user:
            return self._format_error_response("User not found")

        # Can't deactivate yourself
        if user_id == deactivator_id:
            return self._format_error_response("Cannot deactivate yourself")

        # Non-super-admin can't deactivate admins
        deactivator = self.repos.user.get(deactivator_id)
        is_super_admin = any(
            role.role == UserRole.SUPER_ADMIN
            for role in deactivator.center_roles
            if role.is_active
        )

        if not is_super_admin:
            user_roles = [role.role for role in user.center_roles if role.is_active]
            if UserRole.ADMIN in user_roles or UserRole.SUPER_ADMIN in user_roles:
                return self._format_error_response("Cannot deactivate admin users")

        try:
            updated_user = self.repos.user.deactivate_user(user_id)
            return self._format_success_response(
                UserResponse.from_orm(updated_user),
                "User deactivated successfully"
            )

        except Exception as e:
            return self._format_error_response(f"Failed to deactivate user: {str(e)}")

    def activate_user(self, user_id: int, activator_id: int) -> Dict[str, Any]:
        """Activate user account"""
        if not self._check_permissions(activator_id, [UserRole.ADMIN, UserRole.SUPER_ADMIN]):
            return self._format_error_response("Admin access required")

        try:
            updated_user = self.repos.user.activate_user(user_id)
            if not updated_user:
                return self._format_error_response("User not found")

            return self._format_success_response(
                UserResponse.from_orm(updated_user),
                "User activated successfully"
            )

        except Exception as e:
            return self._format_error_response(f"Failed to activate user: {str(e)}")

    def link_telegram(self, user_id: int, telegram_id: int) -> Dict[str, Any]:
        """Link Telegram ID to user account (used by verification service)"""
        # Check if telegram ID is already used
        if self.repos.user.telegram_id_exists(telegram_id):
            return self._format_error_response("Telegram ID already linked to another account")

        try:
            updated_user = self.repos.user.link_telegram(user_id, telegram_id)
            if not updated_user:
                return self._format_error_response("User not found")

            return self._format_success_response(
                UserResponse.from_orm(updated_user),
                "Telegram account linked successfully"
            )

        except Exception as e:
            return self._format_error_response(f"Failed to link Telegram: {str(e)}")

    def get_user_stats(self, learning_center_id: int, requester_id: int) -> Dict[str, Any]:
        """Get user statistics for learning center"""
        if not self._check_permissions(
            requester_id,
            [UserRole.ADMIN, UserRole.SUPER_ADMIN],
            learning_center_id
        ):
            return self._format_error_response("Admin access required")

        stats = self.repos.user.get_user_stats_summary(learning_center_id)
        return self._format_success_response(stats)
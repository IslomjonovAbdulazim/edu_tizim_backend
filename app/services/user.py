from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models import UserRole
from app.schemas import (
    UserCreate, UserUpdate, UserResponse, LoginRequest, LoginResponse,
    UserStats, UserWithDetails
)
from app.services.base import BaseService


class UserService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)

    def create_user(self, user_data: UserCreate) -> Dict[str, Any]:
        """Create new user with validation"""
        # Check if telegram ID already exists
        if self.repos.user.telegram_id_exists(user_data.telegram_id):
            return self._format_error_response("Telegram ID already registered")

        # Check if phone exists in this learning center
        if self.repos.user.phone_exists_in_center(user_data.phone_number, user_data.learning_center_id):
            return self._format_error_response("Phone number already registered in this learning center")

        # Verify learning center exists and is active
        learning_center = self.repos.learning_center.get(user_data.learning_center_id)
        if not learning_center:
            return self._format_error_response("Learning center not found")

        if not learning_center.is_active:
            return self._format_error_response("Learning center subscription expired")

        # Verify branch if provided
        if user_data.branch_id:
            branch = self.repos.branch.get(user_data.branch_id)
            if not branch or branch.learning_center_id != user_data.learning_center_id:
                return self._format_error_response("Invalid branch for this learning center")

        # Create user
        try:
            user = self.repos.user.create(user_data.dict())
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
            return self._format_error_response("User not found")

        if not user.is_active:
            return self._format_error_response("User account is deactivated")

        # Check learning center status
        learning_center = self.repos.learning_center.get(user.learning_center_id)
        if not learning_center or not learning_center.is_active:
            return self._format_error_response("Learning center subscription expired")

        response_data = LoginResponse(
            user=UserResponse.from_orm(user),
            verification_required=not user.is_verified,
            message="Login successful" if user.is_verified else "Phone verification required"
        )

        return self._format_success_response(response_data)

    def get_user(self, user_id: int) -> Optional[UserWithDetails]:
        """Get user with additional details"""
        user = self.repos.user.get(user_id)
        if not user:
            return None

        user_data = UserWithDetails.from_orm(user)
        user_data.learning_center_name = user.learning_center.brand_name if user.learning_center else None
        user_data.branch_title = user.branch.title if user.branch else None

        return user_data

    def update_user(self, user_id: int, update_data: UserUpdate, updater_id: int) -> Dict[str, Any]:
        """Update user with permission checks"""
        user = self.repos.user.get(user_id)
        if not user:
            return self._format_error_response("User not found")

        updater = self.repos.user.get(updater_id)
        if not updater:
            return self._format_error_response("Invalid updater")

        # Permission check: user can update themselves, or admin/super_admin can update others
        can_update = (
                user_id == updater_id or  # Self update
                updater.has_any_role([UserRole.ADMIN, UserRole.SUPER_ADMIN]) or  # Admin update
                (updater.has_role(UserRole.RECEPTION) and user.learning_center_id == updater.learning_center_id)
        # Reception in same center
        )

        if not can_update:
            return self._format_error_response("Insufficient permissions")

        # Update user
        update_dict = update_data.dict(exclude_unset=True)
        updated_user = self.repos.user.update(user_id, update_dict)

        if not updated_user:
            return self._format_error_response("Failed to update user")

        return self._format_success_response(
            UserResponse.from_orm(updated_user),
            "User updated successfully"
        )

    def verify_user(self, user_id: int) -> Dict[str, Any]:
        """Mark user as verified"""
        user = self.repos.user.verify_user(user_id)
        if not user:
            return self._format_error_response("User not found")

        return self._format_success_response(
            UserResponse.from_orm(user),
            "User verified successfully"
        )

    def change_user_role(self, user_id: int, new_role: UserRole, changer_id: int) -> Dict[str, Any]:
        """Change user role with permission checks"""
        user = self.repos.user.get(user_id)
        changer = self.repos.user.get(changer_id)

        if not user or not changer:
            return self._format_error_response("User not found")

        # Only admin and super_admin can change roles
        if not changer.has_any_role([UserRole.ADMIN, UserRole.SUPER_ADMIN]):
            return self._format_error_response("Insufficient permissions")

        # Super admin can change any role, admin can't create other admins or super_admins
        if changer.has_role(UserRole.ADMIN) and new_role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            return self._format_error_response("Cannot assign admin or super_admin role")

        # Same learning center check (except super admin)
        if not changer.has_role(UserRole.SUPER_ADMIN):
            if user.learning_center_id != changer.learning_center_id:
                return self._format_error_response("Can only change roles within same learning center")

        updated_user = self.repos.user.change_role(user_id, new_role)
        return self._format_success_response(
            UserResponse.from_orm(updated_user),
            f"User role changed to {new_role}"
        )

    def get_users_by_center(self, learning_center_id: int, requester_id: int) -> Dict[str, Any]:
        """Get all users in learning center"""
        requester = self.repos.user.get(requester_id)
        if not requester:
            return self._format_error_response("Invalid requester")

        # Permission check
        can_view = (
                requester.has_role(UserRole.SUPER_ADMIN) or
                (requester.learning_center_id == learning_center_id and
                 requester.has_any_role([UserRole.ADMIN, UserRole.RECEPTION, UserRole.GROUP_MANAGER]))
        )

        if not can_view:
            return self._format_error_response("Insufficient permissions")

        users = self.repos.user.get_users_by_center(learning_center_id)
        users_data = [UserResponse.from_orm(user) for user in users]

        return self._format_success_response(users_data)

    def get_users_by_role(self, role: UserRole, learning_center_id: int, requester_id: int) -> Dict[str, Any]:
        """Get users by role in learning center"""
        # Permission check
        if not self._check_permissions(requester_id, [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.RECEPTION],
                                       learning_center_id):
            return self._format_error_response("Insufficient permissions")

        users = self.repos.user.get_users_by_role(role, learning_center_id)
        users_data = [UserResponse.from_orm(user) for user in users]

        return self._format_success_response(users_data)

    def search_users(self, query: str, learning_center_id: int, requester_id: int) -> Dict[str, Any]:
        """Search users by name or phone"""
        if not self._check_permissions(requester_id, [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.RECEPTION],
                                       learning_center_id):
            return self._format_error_response("Insufficient permissions")

        users = self.repos.user.search_users(learning_center_id, query)
        users_data = [UserResponse.from_orm(user) for user in users]

        return self._format_success_response(users_data)

    def deactivate_user(self, user_id: int, deactivator_id: int) -> Dict[str, Any]:
        """Deactivate user"""
        user = self.repos.user.get(user_id)
        deactivator = self.repos.user.get(deactivator_id)

        if not user or not deactivator:
            return self._format_error_response("User not found")

        # Permission check
        can_deactivate = (
                deactivator.has_role(UserRole.SUPER_ADMIN) or
                (deactivator.has_role(UserRole.ADMIN) and user.learning_center_id == deactivator.learning_center_id)
        )

        if not can_deactivate:
            return self._format_error_response("Insufficient permissions")

        # Can't deactivate yourself or other admins/super_admins
        if user_id == deactivator_id:
            return self._format_error_response("Cannot deactivate yourself")

        if user.has_any_role([UserRole.ADMIN, UserRole.SUPER_ADMIN]) and not deactivator.has_role(UserRole.SUPER_ADMIN):
            return self._format_error_response("Cannot deactivate admin or super_admin")

        updated_user = self.repos.user.deactivate_user(user_id)
        return self._format_success_response(
            UserResponse.from_orm(updated_user),
            "User deactivated successfully"
        )

    def activate_user(self, user_id: int, activator_id: int) -> Dict[str, Any]:
        """Activate user"""
        # Similar logic to deactivate but for activation
        user = self.repos.user.get(user_id)
        activator = self.repos.user.get(activator_id)

        if not user or not activator:
            return self._format_error_response("User not found")

        # Permission check
        can_activate = (
                activator.has_role(UserRole.SUPER_ADMIN) or
                (activator.has_role(UserRole.ADMIN) and user.learning_center_id == activator.learning_center_id)
        )

        if not can_activate:
            return self._format_error_response("Insufficient permissions")

        updated_user = self.repos.user.activate_user(user_id)
        return self._format_success_response(
            UserResponse.from_orm(updated_user),
            "User activated successfully"
        )

    def get_user_stats(self, user_id: int) -> Optional[UserStats]:
        """Get comprehensive user statistics"""
        user = self.repos.user.get(user_id)
        if not user:
            return None

        # Get progress stats
        progress_records = self.repos.progress.get_user_progress(user_id)
        total_points = sum(p.points for p in progress_records)
        lessons_completed = sum(1 for p in progress_records if p.is_completed)
        perfect_lessons = self.repos.progress.get_perfect_lessons_count(user_id)

        # Get gamification stats
        weaklist_solved = self.repos.weak_word.get_mastered_words_count(user_id)
        position_improvements = self.repos.leaderboard.get_position_improvements_count(user_id)
        badges_count = self.repos.badge.get_total_badges_count(user_id)

        return UserStats(
            user_id=user_id,
            total_points=total_points,
            lessons_completed=lessons_completed,
            perfect_lessons=perfect_lessons,
            weaklist_solved=weaklist_solved,
            position_improvements=position_improvements,
            current_streak=0,  # TODO: Implement streak calculation
            badges_count=badges_count
        )
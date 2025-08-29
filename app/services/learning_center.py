from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import date, timedelta
from app.models import UserRole
from app.schemas import (
    LearningCenterCreate, LearningCenterUpdate, LearningCenterResponse, LearningCenterWithStats,
    BranchCreate, BranchUpdate, BranchResponse, BranchWithStats,
    PaymentCreate, PaymentResponse
)
from app.services.base import BaseService


class LearningCenterService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)

    def create_learning_center(self, center_data: LearningCenterCreate, creator_id: int) -> Dict[str, Any]:
        """Create new learning center (super admin only)"""
        creator = self.repos.user.get(creator_id)
        if not creator or not creator.has_role(UserRole.SUPER_ADMIN):
            return self._format_error_response("Only super admin can create learning centers")

        # Check if phone already exists
        existing = self.repos.learning_center.get_by_phone(center_data.phone_number)
        if existing:
            return self._format_error_response("Phone number already registered")

        try:
            center = self.repos.learning_center.create(center_data.dict())
            return self._format_success_response(
                LearningCenterResponse.from_orm(center),
                "Learning center created successfully"
            )
        except Exception as e:
            return self._format_error_response(f"Failed to create learning center: {str(e)}")

    def update_learning_center(self, center_id: int, update_data: LearningCenterUpdate, updater_id: int) -> Dict[
        str, Any]:
        """Update learning center"""
        center = self.repos.learning_center.get(center_id)
        if not center:
            return self._format_error_response("Learning center not found")

        updater = self.repos.user.get(updater_id)
        if not updater:
            return self._format_error_response("Invalid updater")

        # Permission check: super admin or admin of this center
        can_update = (
                updater.has_role(UserRole.SUPER_ADMIN) or
                (updater.has_role(UserRole.ADMIN) and updater.learning_center_id == center_id)
        )

        if not can_update:
            return self._format_error_response("Insufficient permissions")

        # Update center
        update_dict = update_data.dict(exclude_unset=True)
        updated_center = self.repos.learning_center.update(center_id, update_dict)

        if not updated_center:
            return self._format_error_response("Failed to update learning center")

        return self._format_success_response(
            LearningCenterResponse.from_orm(updated_center),
            "Learning center updated successfully"
        )

    def add_payment(self, payment_data: PaymentCreate, processor_id: int) -> Dict[str, Any]:
        """Add payment and extend subscription"""
        processor = self.repos.user.get(processor_id)
        if not processor or not processor.has_any_role([UserRole.SUPER_ADMIN, UserRole.ADMIN]):
            return self._format_error_response("Only admin or super admin can process payments")

        center = self.repos.learning_center.get(payment_data.learning_center_id)
        if not center:
            return self._format_error_response("Learning center not found")

        # Permission check for admin (can only process payments for their own center)
        if processor.has_role(UserRole.ADMIN) and processor.learning_center_id != payment_data.learning_center_id:
            return self._format_error_response("Can only process payments for your own learning center")

        try:
            # Create payment record
            payment = self.repos.payment.create(payment_data.dict())

            # Add days to learning center
            updated_center = self.repos.learning_center.add_payment_days(
                payment_data.learning_center_id,
                payment_data.days_added,
                payment_data.amount
            )

            return self._format_success_response({
                "payment": PaymentResponse.from_orm(payment),
                "learning_center": LearningCenterResponse.from_orm(updated_center)
            }, f"Payment processed successfully. Added {payment_data.days_added} days")

        except Exception as e:
            return self._format_error_response(f"Failed to process payment: {str(e)}")

    def get_learning_center_with_stats(self, center_id: int, requester_id: int) -> Dict[str, Any]:
        """Get learning center with statistics"""
        center = self.repos.learning_center.get(center_id)
        if not center:
            return self._format_error_response("Learning center not found")

        requester = self.repos.user.get(requester_id)
        if not requester:
            return self._format_error_response("Invalid requester")

        # Permission check
        can_view = (
                requester.has_role(UserRole.SUPER_ADMIN) or
                (requester.learning_center_id == center_id and
                 requester.has_any_role([UserRole.ADMIN, UserRole.RECEPTION]))
        )

        if not can_view:
            return self._format_error_response("Insufficient permissions")

        # Get statistics
        users = self.repos.user.get_users_by_center(center_id)
        active_users = [u for u in users if u.is_active]
        branches = self.repos.branch.get_by_center(center_id)
        courses = self.repos.course.get_by_center(center_id)

        center_data = LearningCenterWithStats.from_orm(center)
        center_data.total_users = len(users)
        center_data.active_users = len(active_users)
        center_data.total_branches = len(branches)
        center_data.total_courses = len(courses)

        return self._format_success_response(center_data)

    def check_expiring_centers(self) -> List[Dict[str, Any]]:
        """Check for expiring learning centers (system cron job)"""
        expiring_centers = self.repos.learning_center.get_expiring_soon(days=7)
        expired_centers = self.repos.learning_center.get_expired_centers()

        notifications = []

        # Notify expiring centers
        for center in expiring_centers:
            notifications.append({
                "center_id": center.id,
                "brand_name": center.brand_name,
                "days_remaining": center.remaining_days,
                "status": "expiring_soon",
                "message": f"Learning center '{center.brand_name}' expires in {center.remaining_days} days"
            })

        # Block expired centers
        for center in expired_centers:
            if center.is_active:  # Only block if still active
                self.repos.learning_center.block_center(center.id)
                notifications.append({
                    "center_id": center.id,
                    "brand_name": center.brand_name,
                    "days_remaining": center.remaining_days,
                    "status": "expired_blocked",
                    "message": f"Learning center '{center.brand_name}' has been blocked due to expired subscription"
                })

        return notifications

    def daily_subscription_deduction(self) -> Dict[str, Any]:
        """Daily cron job to deduct days from all centers"""
        centers = self.repos.learning_center.get_active_centers()
        processed = 0
        blocked = 0

        for center in centers:
            updated_center = self.repos.learning_center.deduct_day(center.id)
            processed += 1

            if updated_center and not updated_center.is_active:
                blocked += 1

        return {
            "processed_centers": processed,
            "newly_blocked_centers": blocked,
            "message": f"Processed {processed} centers, {blocked} newly blocked"
        }

    def get_payment_history(self, center_id: int, requester_id: int) -> Dict[str, Any]:
        """Get payment history for learning center"""
        if not self._check_permissions(requester_id, [UserRole.ADMIN, UserRole.SUPER_ADMIN], center_id):
            return self._format_error_response("Insufficient permissions")

        payments = self.repos.payment.get_by_center(center_id)
        payments_data = [PaymentResponse.from_orm(p) for p in payments]

        return self._format_success_response(payments_data)

    def get_all_centers(self, requester_id: int) -> Dict[str, Any]:
        """Get all learning centers (super admin only)"""
        if not self._check_permissions(requester_id, [UserRole.SUPER_ADMIN]):
            return self._format_error_response("Super admin access required")

        centers = self.repos.learning_center.get_multi()
        centers_data = [LearningCenterResponse.from_orm(c) for c in centers]

        return self._format_success_response(centers_data)


class BranchService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)

    def create_branch(self, branch_data: BranchCreate, creator_id: int) -> Dict[str, Any]:
        """Create new branch"""
        center = self.repos.learning_center.get(branch_data.learning_center_id)
        if not center:
            return self._format_error_response("Learning center not found")

        # Permission check
        if not self._check_permissions(creator_id, [UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       branch_data.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        # Check branch limit
        existing_branches = self.repos.branch.get_by_center(branch_data.learning_center_id)
        if len(existing_branches) >= center.max_branches:
            return self._format_error_response(f"Maximum branch limit ({center.max_branches}) reached")

        try:
            branch = self.repos.branch.create(branch_data.dict())
            return self._format_success_response(
                BranchResponse.from_orm(branch),
                "Branch created successfully"
            )
        except Exception as e:
            return self._format_error_response(f"Failed to create branch: {str(e)}")

    def update_branch(self, branch_id: int, update_data: BranchUpdate, updater_id: int) -> Dict[str, Any]:
        """Update branch"""
        branch = self.repos.branch.get(branch_id)
        if not branch:
            return self._format_error_response("Branch not found")

        # Permission check
        if not self._check_permissions(updater_id, [UserRole.ADMIN, UserRole.SUPER_ADMIN], branch.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        update_dict = update_data.dict(exclude_unset=True)
        updated_branch = self.repos.branch.update(branch_id, update_dict)

        if not updated_branch:
            return self._format_error_response("Failed to update branch")

        return self._format_success_response(
            BranchResponse.from_orm(updated_branch),
            "Branch updated successfully"
        )

    def get_branches_by_center(self, center_id: int, requester_id: int) -> Dict[str, Any]:
        """Get all branches for learning center"""
        if not self._check_permissions(requester_id, [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.RECEPTION],
                                       center_id):
            return self._format_error_response("Insufficient permissions")

        branches = self.repos.branch.get_by_center(center_id)
        branches_data = []

        for branch in branches:
            branch_stats = BranchWithStats.from_orm(branch)
            # Add statistics (you can expand this)
            groups = self.repos.group.get_by_branch(branch.id)
            active_groups = [g for g in groups if g.is_active]

            branch_stats.total_groups = len(groups)
            branch_stats.active_groups = len(active_groups)
            branch_stats.total_students = sum(g.student_count for g in groups)

            branches_data.append(branch_stats)

        return self._format_success_response(branches_data)

    def find_nearby_branches(self, latitude: float, longitude: float, radius_km: float = 10) -> Dict[str, Any]:
        """Find branches within radius (simplified - you'd want proper geo calculation)"""
        # This is a simplified implementation
        # In production, you'd use PostGIS or similar for proper geographic queries
        lat_diff = radius_km / 111.0  # Rough conversion
        lng_diff = radius_km / (111.0 * abs(latitude))

        branches = self.repos.branch.get_by_coordinates(
            latitude - lat_diff, latitude + lat_diff,
            longitude - lng_diff, longitude + lng_diff
        )

        branches_data = [BranchResponse.from_orm(b) for b in branches]
        return self._format_success_response(branches_data)

    def deactivate_branch(self, branch_id: int, deactivator_id: int) -> Dict[str, Any]:
        """Deactivate branch"""
        branch = self.repos.branch.get(branch_id)
        if not branch:
            return self._format_error_response("Branch not found")

        if not self._check_permissions(deactivator_id, [UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       branch.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        updated_branch = self.repos.branch.deactivate_branch(branch_id)
        return self._format_success_response(
            BranchResponse.from_orm(updated_branch),
            "Branch deactivated successfully"
        )
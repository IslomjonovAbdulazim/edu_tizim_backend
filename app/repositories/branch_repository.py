from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc
from datetime import datetime, date, timedelta
from app.models.branch import Branch
from app.models.user import User
from app.models.group import Group
from app.models.student import Student
from app.repositories.base_repository import BaseRepository
from app.services.limit_validation_service import LimitValidationService
import math


class BranchRepository(BaseRepository[Branch]):
    def __init__(self):
        super().__init__(Branch)

    def create_with_limit_check(self, db: Session, branch_data: Dict[str, Any], check_limits: bool = True) -> Dict[
        str, Any]:
        """Create branch with limit validation"""
        learning_center_id = branch_data.get("learning_center_id")

        if check_limits and learning_center_id:
            limit_service = LimitValidationService(db)
            validation = limit_service.validate_branch_creation(learning_center_id)

            if not validation["can_proceed"]:
                return {
                    "success": False,
                    "message": validation["message"],
                    "error_code": validation.get("error_code", "BRANCH_LIMIT_EXCEEDED"),
                    "branch": None
                }

        # Create the branch
        branch = self.create(db, branch_data)

        return {
            "success": True,
            "message": "Branch created successfully",
            "branch": branch
        }

    def get_by_learning_center(self, db: Session, learning_center_id: int, active_only: bool = True) -> List[Branch]:
        """Get branches by learning center"""
        query = db.query(Branch).filter(Branch.learning_center_id == learning_center_id)

        if active_only:
            query = query.filter(Branch.is_active == True)

        return query.options(
            joinedload(Branch.learning_center)
        ).order_by(Branch.name).all()

    def get_with_statistics(self, db: Session, branch_id: int) -> Optional[Dict[str, Any]]:
        """Get branch with comprehensive statistics"""
        branch = self.get(db, branch_id)
        if not branch:
            return None

        # Get group counts
        total_groups = db.query(Group).filter(Group.branch_id == branch_id).count()
        active_groups = db.query(Group).filter(
            and_(Group.branch_id == branch_id, Group.is_active == True)
        ).count()

        # Get student counts across all groups in this branch
        total_students = db.query(func.count(Student.id.distinct())).select_from(Group).join(
            Group.students
        ).filter(Group.branch_id == branch_id).scalar() or 0

        # Get staff assigned to this branch
        staff_count = db.query(User).filter(User.branch_id == branch_id).count()

        return {
            "branch": branch,
            "statistics": {
                "groups": {
                    "total": total_groups,
                    "active": active_groups,
                    "inactive": total_groups - active_groups
                },
                "students": {
                    "total": total_students
                },
                "staff": {
                    "total_assigned": staff_count
                }
            }
        }

    def search_branches(
            self,
            db: Session,
            search_term: str,
            learning_center_id: Optional[int] = None,
            active_only: bool = True,
            skip: int = 0,
            limit: int = 100
    ) -> List[Branch]:
        """Search branches by name, address"""
        query = db.query(Branch).filter(
            or_(
                Branch.name.ilike(f"%{search_term}%"),
                Branch.address.ilike(f"%{search_term}%")
            )
        )

        if learning_center_id:
            query = query.filter(Branch.learning_center_id == learning_center_id)

        if active_only:
            query = query.filter(Branch.is_active == True)

        return query.options(
            joinedload(Branch.learning_center)
        ).offset(skip).limit(limit).all()

    def find_branches_by_location(
            self,
            db: Session,
            latitude: float,
            longitude: float,
            radius_km: float,
            learning_center_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Find branches within specified radius of a location"""
        query = db.query(Branch).filter(
            and_(
                Branch.latitude.isnot(None),
                Branch.longitude.isnot(None),
                Branch.is_active == True
            )
        )

        if learning_center_id:
            query = query.filter(Branch.learning_center_id == learning_center_id)

        branches = query.all()

        # Calculate distances and filter
        nearby_branches = []
        for branch in branches:
            distance = self._calculate_distance(
                latitude, longitude,
                float(branch.latitude), float(branch.longitude)
            )

            if distance <= radius_km:
                nearby_branches.append({
                    "branch": branch,
                    "distance_km": round(distance, 2),
                    "is_nearby": True
                })

        # Sort by distance
        nearby_branches.sort(key=lambda x: x["distance_km"])
        return nearby_branches

    def assign_staff_to_branch(self, db: Session, user_id: int, branch_id: int) -> bool:
        """Assign staff member to a branch"""
        user = db.query(User).filter(User.id == user_id).first()
        branch = self.get(db, branch_id)

        if user and branch:
            user.branch_id = branch_id
            db.commit()
            return True
        return False

    def unassign_staff_from_branch(self, db: Session, user_id: int) -> bool:
        """Remove staff assignment from branch"""
        user = db.query(User).filter(User.id == user_id).first()

        if user:
            user.branch_id = None
            db.commit()
            return True
        return False

    def get_branch_staff(self, db: Session, branch_id: int) -> List[User]:
        """Get all staff assigned to a branch"""
        return db.query(User).filter(User.branch_id == branch_id).all()

    def get_branch_groups(self, db: Session, branch_id: int, active_only: bool = True) -> List[Group]:
        """Get all groups in a branch"""
        query = db.query(Group).filter(Group.branch_id == branch_id)

        if active_only:
            query = query.filter(Group.is_active == True)

        return query.options(
            joinedload(Group.course),
            joinedload(Group.teacher),
            joinedload(Group.students)
        ).all()

    def transfer_groups_to_branch(self, db: Session, group_ids: List[int], target_branch_id: int) -> Dict[str, Any]:
        """Transfer groups to a different branch"""
        target_branch = self.get(db, target_branch_id)
        if not target_branch:
            return {"success": False, "message": "Target branch not found"}

        groups = db.query(Group).filter(Group.id.in_(group_ids)).all()

        transferred_count = 0
        failed_transfers = []

        for group in groups:
            try:
                # Ensure same learning center
                if group.learning_center_id != target_branch.learning_center_id:
                    failed_transfers.append({
                        "group_id": group.id,
                        "error": "Cannot transfer to different learning center"
                    })
                    continue

                group.branch_id = target_branch_id
                transferred_count += 1
            except Exception as e:
                failed_transfers.append({
                    "group_id": group.id,
                    "error": str(e)
                })

        db.commit()

        return {
            "success": True,
            "transferred_count": transferred_count,
            "failed_transfers": failed_transfers,
            "message": f"Successfully transferred {transferred_count} groups"
        }

    def get_branch_analytics(
            self,
            db: Session,
            branch_id: int,
            days: int = 30
    ) -> Dict[str, Any]:
        """Get comprehensive analytics for a branch"""
        branch = self.get(db, branch_id)
        if not branch:
            return {}

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Group performance
        groups = self.get_branch_groups(db, branch_id, active_only=True)
        group_performance = []

        for group in groups:
            group_performance.append({
                "group_id": group.id,
                "group_name": group.name,
                "students": len(group.students),
                "capacity_utilization": (
                            len(group.students) / group.max_capacity * 100) if group.max_capacity > 0 else 0,
                "teacher_assigned": group.teacher is not None
            })

        return {
            "branch": {
                "id": branch.id,
                "name": branch.name,
                "address": branch.address
            },
            "analysis_period": {
                "start_date": start_date,
                "end_date": end_date,
                "days": days
            },
            "group_performance": group_performance,
            "staff_count": len(self.get_branch_staff(db, branch_id)),
            "total_students": sum(len(group.students) for group in groups),
            "total_groups": len(groups)
        }

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula"""
        # Convert latitude and longitude to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))

        # Radius of earth in kilometers
        r = 6371

        return c * r

    def get_branch_statistics(self, db: Session, learning_center_id: Optional[int] = None) -> Dict[str, Any]:
        """Get comprehensive branch statistics"""
        base_query = db.query(Branch)

        if learning_center_id:
            base_query = base_query.filter(Branch.learning_center_id == learning_center_id)

        total_branches = base_query.count()
        active_branches = base_query.filter(Branch.is_active == True).count()

        # Branches with coordinates
        branches_with_location = base_query.filter(
            and_(Branch.latitude.isnot(None), Branch.longitude.isnot(None))
        ).count()

        return {
            "total_branches": total_branches,
            "active_branches": active_branches,
            "inactive_branches": total_branches - active_branches,
            "branches_with_location": branches_with_location,
            "location_coverage": (branches_with_location / total_branches * 100) if total_branches > 0 else 0
        }
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.learning_center import LearningCenter
from app.models.branch import Branch
from app.models.student import Student
from app.models.user import User
from app.constants.roles import UserRole


class LimitValidationService:
    """Service to validate learning center limits for branches and students"""

    def __init__(self, db: Session):
        self.db = db

    def check_branch_limit(self, learning_center_id: int) -> Dict[str, Any]:
        """Check if learning center can add more branches"""
        center = self.db.query(LearningCenter).filter(LearningCenter.id == learning_center_id).first()

        if not center:
            return {
                "success": False,
                "message": "Learning center not found",
                "can_proceed": False
            }

        current_branches = self.db.query(Branch).filter(Branch.learning_center_id == learning_center_id).count()
        remaining = max(0, center.max_branches - current_branches)
        can_add = current_branches < center.max_branches

        return {
            "success": True,
            "message": f"Branch limit check: {current_branches}/{center.max_branches} branches used",
            "current_count": current_branches,
            "limit": center.max_branches,
            "remaining": remaining,
            "can_proceed": can_add,
            "utilization_percentage": (current_branches / center.max_branches * 100) if center.max_branches > 0 else 0
        }

    def check_student_limit(self, learning_center_id: int, additional_students: int = 1) -> Dict[str, Any]:
        """Check if learning center can add more students"""
        center = self.db.query(LearningCenter).filter(LearningCenter.id == learning_center_id).first()

        if not center:
            return {
                "success": False,
                "message": "Learning center not found",
                "can_proceed": False
            }

        # Count current students in this learning center
        current_students = self.db.query(Student).join(User).filter(
            User.learning_center_id == learning_center_id,
            User.role == UserRole.STUDENT,
            User.is_active == True
        ).count()

        remaining = max(0, center.max_students - current_students)
        can_add = (current_students + additional_students) <= center.max_students

        return {
            "success": True,
            "message": f"Student limit check: {current_students}/{center.max_students} students enrolled",
            "current_count": current_students,
            "limit": center.max_students,
            "remaining": remaining,
            "can_proceed": can_add,
            "additional_requested": additional_students,
            "would_exceed": not can_add,
            "utilization_percentage": (current_students / center.max_students * 100) if center.max_students > 0 else 0
        }

    def validate_branch_creation(self, learning_center_id: int) -> Dict[str, Any]:
        """Validate if a new branch can be created"""
        result = self.check_branch_limit(learning_center_id)

        if not result["success"]:
            return result

        if not result["can_proceed"]:
            return {
                "success": False,
                "message": f"Cannot create branch: Maximum of {result['limit']} branches allowed. Currently have {result['current_count']} branches.",
                "error_code": "BRANCH_LIMIT_EXCEEDED",
                "can_proceed": False,
                "current_count": result["current_count"],
                "limit": result["limit"]
            }

        return {
            "success": True,
            "message": "Branch creation allowed",
            "can_proceed": True,
            "remaining_slots": result["remaining"]
        }

    def validate_student_creation(self, learning_center_id: int, count: int = 1) -> Dict[str, Any]:
        """Validate if new students can be created"""
        result = self.check_student_limit(learning_center_id, count)

        if not result["success"]:
            return result

        if not result["can_proceed"]:
            return {
                "success": False,
                "message": f"Cannot add {count} student(s): Maximum of {result['limit']} students allowed. Currently have {result['current_count']} students. Only {result['remaining']} slots available.",
                "error_code": "STUDENT_LIMIT_EXCEEDED",
                "can_proceed": False,
                "current_count": result["current_count"],
                "limit": result["limit"],
                "remaining": result["remaining"],
                "requested": count
            }

        return {
            "success": True,
            "message": f"Student creation allowed for {count} student(s)",
            "can_proceed": True,
            "remaining_slots": result["remaining"] - count
        }

    def validate_limit_update(self, learning_center_id: int, new_max_branches: Optional[int] = None,
                              new_max_students: Optional[int] = None) -> Dict[str, Any]:
        """Validate if limits can be updated (cannot be set below current count)"""
        center = self.db.query(LearningCenter).filter(LearningCenter.id == learning_center_id).first()

        if not center:
            return {
                "success": False,
                "message": "Learning center not found",
                "can_proceed": False
            }

        errors = []
        warnings = []

        # Check branch limit
        if new_max_branches is not None:
            current_branches = self.db.query(Branch).filter(Branch.learning_center_id == learning_center_id).count()
            if new_max_branches < current_branches:
                errors.append(
                    f"Cannot set branch limit to {new_max_branches}: Currently have {current_branches} branches")
            elif new_max_branches < center.max_branches:
                warnings.append(f"Reducing branch limit from {center.max_branches} to {new_max_branches}")

        # Check student limit
        if new_max_students is not None:
            current_students = self.db.query(Student).join(User).filter(
                User.learning_center_id == learning_center_id,
                User.role == UserRole.STUDENT,
                User.is_active == True
            ).count()
            if new_max_students < current_students:
                errors.append(
                    f"Cannot set student limit to {new_max_students}: Currently have {current_students} students")
            elif new_max_students < center.max_students:
                warnings.append(f"Reducing student limit from {center.max_students} to {new_max_students}")

        if errors:
            return {
                "success": False,
                "message": "Limit update validation failed",
                "errors": errors,
                "warnings": warnings,
                "can_proceed": False
            }

        return {
            "success": True,
            "message": "Limit update validation passed",
            "warnings": warnings,
            "can_proceed": True
        }

    def get_center_utilization_report(self, learning_center_id: int) -> Dict[str, Any]:
        """Get comprehensive utilization report for a learning center"""
        center = self.db.query(LearningCenter).filter(LearningCenter.id == learning_center_id).first()

        if not center:
            return {"error": "Learning center not found"}

        branch_check = self.check_branch_limit(learning_center_id)
        student_check = self.check_student_limit(learning_center_id, 0)

        # Get growth recommendations
        recommendations = []

        if branch_check["utilization_percentage"] >= 80:
            recommendations.append("Consider increasing branch limit - currently at 80%+ utilization")

        if student_check["utilization_percentage"] >= 80:
            recommendations.append("Consider increasing student limit - currently at 80%+ utilization")

        if branch_check["utilization_percentage"] < 50:
            recommendations.append("Branch capacity underutilized - opportunity for expansion")

        if student_check["utilization_percentage"] < 50:
            recommendations.append("Student capacity underutilized - opportunity for marketing")

        return {
            "center_id": learning_center_id,
            "center_name": center.name,
            "limits": {
                "branches": {
                    "current": branch_check["current_count"],
                    "limit": branch_check["limit"],
                    "remaining": branch_check["remaining"],
                    "utilization": round(branch_check["utilization_percentage"], 1)
                },
                "students": {
                    "current": student_check["current_count"],
                    "limit": student_check["limit"],
                    "remaining": student_check["remaining"],
                    "utilization": round(student_check["utilization_percentage"], 1)
                }
            },
            "status": {
                "can_add_branch": branch_check["can_proceed"],
                "can_add_student": student_check["can_proceed"],
                "near_branch_limit": branch_check["utilization_percentage"] >= 90,
                "near_student_limit": student_check["utilization_percentage"] >= 90
            },
            "recommendations": recommendations
        }

    def get_all_centers_utilization(self) -> List[Dict[str, Any]]:
        """Get utilization report for all learning centers"""
        centers = self.db.query(LearningCenter).filter(LearningCenter.is_active == True).all()

        reports = []
        for center in centers:
            report = self.get_center_utilization_report(center.id)
            if "error" not in report:
                reports.append(report)

        return reports
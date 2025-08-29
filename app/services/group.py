from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models import UserRole
from app.schemas import (
    GroupCreate, GroupUpdate, GroupResponse, GroupWithDetails,
    StudentGroupAssignment, StudentGroupBulkAssignment, GroupStudentsList
)
from app.services.base import BaseService


class GroupService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)

    def create_group(self, group_data: GroupCreate, creator_id: int) -> Dict[str, Any]:
        """Create new group"""
        creator = self.repos.user.get(creator_id)
        if not creator:
            return self._format_error_response("User not found")

        # Verify branch exists and get learning center
        branch = self.repos.branch.get(group_data.branch_id)
        if not branch:
            return self._format_error_response("Branch not found")

        # Permission check
        if not self._check_permissions(creator_id, [UserRole.GROUP_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       branch.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        # Verify course if provided
        if group_data.course_id:
            course = self.repos.course.get(group_data.course_id)
            if not course or course.learning_center_id != branch.learning_center_id:
                return self._format_error_response("Invalid course for this learning center")

        # Verify teacher if provided
        if group_data.teacher_id:
            teacher = self.repos.user.get(group_data.teacher_id)
            if not teacher or not teacher.has_role(
                    UserRole.TEACHER) or teacher.learning_center_id != branch.learning_center_id:
                return self._format_error_response("Invalid teacher for this learning center")

        try:
            group = self.repos.group.create(group_data.dict())
            return self._format_success_response(
                GroupResponse.from_orm(group),
                "Group created successfully"
            )
        except Exception as e:
            return self._format_error_response(f"Failed to create group: {str(e)}")

    def update_group(self, group_id: int, update_data: GroupUpdate, updater_id: int) -> Dict[str, Any]:
        """Update group"""
        group = self.repos.group.get(group_id)
        if not group:
            return self._format_error_response("Group not found")

        # Permission check
        if not self._check_permissions(updater_id, [UserRole.GROUP_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       group.branch.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        # Validate course if being updated
        if update_data.course_id is not None:
            if update_data.course_id:  # Not setting to None
                course = self.repos.course.get(update_data.course_id)
                if not course or course.learning_center_id != group.branch.learning_center_id:
                    return self._format_error_response("Invalid course for this learning center")

        # Validate teacher if being updated
        if update_data.teacher_id is not None:
            if update_data.teacher_id:  # Not setting to None
                teacher = self.repos.user.get(update_data.teacher_id)
                if not teacher or not teacher.has_role(
                        UserRole.TEACHER) or teacher.learning_center_id != group.branch.learning_center_id:
                    return self._format_error_response("Invalid teacher for this learning center")

        try:
            update_dict = update_data.dict(exclude_unset=True)
            updated_group = self.repos.group.update(group_id, update_dict)

            return self._format_success_response(
                GroupResponse.from_orm(updated_group),
                "Group updated successfully"
            )
        except Exception as e:
            return self._format_error_response(f"Failed to update group: {str(e)}")

    def get_group_with_details(self, group_id: int, requester_id: int) -> Dict[str, Any]:
        """Get group with detailed information"""
        group = self.repos.group.get_with_students(group_id)
        if not group:
            return self._format_error_response("Group not found")

        # Permission check
        requester = self.repos.user.get(requester_id)
        if not requester:
            return self._format_error_response("Invalid requester")

        can_view = (
                requester.has_role(UserRole.SUPER_ADMIN) or
                (requester.learning_center_id == group.branch.learning_center_id and
                 requester.has_any_role(
                     [UserRole.ADMIN, UserRole.GROUP_MANAGER, UserRole.TEACHER, UserRole.RECEPTION])) or
                (requester.id in [s.id for s in group.students])  # Student in the group
        )

        if not can_view:
            return self._format_error_response("Insufficient permissions")

        # Create detailed response
        group_details = GroupWithDetails.from_orm(group)
        group_details.branch_title = group.branch.title
        group_details.course_name = group.course.name if group.course else None

        # Include student details if requester has permission
        if requester.has_any_role([UserRole.ADMIN, UserRole.GROUP_MANAGER, UserRole.TEACHER, UserRole.SUPER_ADMIN]):
            from app.schemas import UserResponse
            group_details.students = [UserResponse.from_orm(student) for student in group.students]

        return self._format_success_response(group_details)

    def get_groups_by_branch(self, branch_id: int, requester_id: int) -> Dict[str, Any]:
        """Get all groups in branch"""
        branch = self.repos.branch.get(branch_id)
        if not branch:
            return self._format_error_response("Branch not found")

        # Permission check
        if not self._check_permissions(requester_id, [UserRole.GROUP_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN,
                                                      UserRole.RECEPTION], branch.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        groups = self.repos.group.get_by_branch(branch_id)
        groups_data = []

        for group in groups:
            group_response = GroupResponse.from_orm(group)
            groups_data.append(group_response)

        return self._format_success_response(groups_data)

    def get_teacher_groups(self, teacher_id: int, requester_id: int) -> Dict[str, Any]:
        """Get groups assigned to teacher"""
        teacher = self.repos.user.get(teacher_id)
        if not teacher or not teacher.has_role(UserRole.TEACHER):
            return self._format_error_response("Teacher not found")

        # Permission check
        can_view = (
                teacher_id == requester_id or  # Teacher viewing own groups
                self._check_permissions(requester_id, [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.GROUP_MANAGER],
                                        teacher.learning_center_id)
        )

        if not can_view:
            return self._format_error_response("Insufficient permissions")

        groups = self.repos.group.get_by_teacher(teacher_id)
        groups_data = [GroupResponse.from_orm(group) for group in groups]

        return self._format_success_response(groups_data)

    def add_student_to_group(self, assignment: StudentGroupAssignment, assigner_id: int) -> Dict[str, Any]:
        """Add single student to group"""
        group = self.repos.group.get(assignment.group_id)
        if not group:
            return self._format_error_response("Group not found")

        student = self.repos.user.get(assignment.user_id)
        if not student or not student.has_role(UserRole.STUDENT):
            return self._format_error_response("Student not found")

        # Permission check
        if not self._check_permissions(assigner_id, [UserRole.GROUP_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       group.branch.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        # Check if student is from same learning center
        if student.learning_center_id != group.branch.learning_center_id:
            return self._format_error_response("Student must be from the same learning center")

        # Add student to group
        success = self.repos.group.add_student_to_group(assignment.user_id, assignment.group_id)

        if not success:
            return self._format_error_response("Student is already in this group or failed to add")

        # Get updated group info
        updated_group = self.repos.group.get(assignment.group_id)

        return self._format_success_response(
            GroupResponse.from_orm(updated_group),
            f"Student {student.full_name} added to group successfully"
        )

    def add_students_bulk(self, bulk_assignment: StudentGroupBulkAssignment, assigner_id: int) -> Dict[str, Any]:
        """Add multiple students to group"""
        group = self.repos.group.get(bulk_assignment.group_id)
        if not group:
            return self._format_error_response("Group not found")

        # Permission check
        if not self._check_permissions(assigner_id, [UserRole.GROUP_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       group.branch.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        # Verify all users are students from same learning center
        students = []
        for user_id in bulk_assignment.user_ids:
            user = self.repos.user.get(user_id)
            if not user or not user.has_role(UserRole.STUDENT):
                return self._format_error_response(f"User {user_id} is not a valid student")

            if user.learning_center_id != group.branch.learning_center_id:
                return self._format_error_response(f"Student {user.full_name} is not from the same learning center")

            students.append(user)

        # Add students to group
        added_count = self.repos.group.add_students_to_group(bulk_assignment.user_ids, bulk_assignment.group_id)

        # Get updated group info
        updated_group = self.repos.group.get(bulk_assignment.group_id)

        return self._format_success_response({
            "group": GroupResponse.from_orm(updated_group),
            "added_count": added_count,
            "total_requested": len(bulk_assignment.user_ids)
        }, f"Added {added_count} out of {len(bulk_assignment.user_ids)} students to group")

    def remove_student_from_group(self, assignment: StudentGroupAssignment, remover_id: int) -> Dict[str, Any]:
        """Remove student from group"""
        group = self.repos.group.get(assignment.group_id)
        if not group:
            return self._format_error_response("Group not found")

        student = self.repos.user.get(assignment.user_id)
        if not student:
            return self._format_error_response("Student not found")

        # Permission check
        if not self._check_permissions(remover_id, [UserRole.GROUP_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       group.branch.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        # Remove student from group
        success = self.repos.group.remove_student_from_group(assignment.user_id, assignment.group_id)

        if not success:
            return self._format_error_response("Student was not in this group or failed to remove")

        # Get updated group info
        updated_group = self.repos.group.get(assignment.group_id)

        return self._format_success_response(
            GroupResponse.from_orm(updated_group),
            f"Student {student.full_name} removed from group successfully"
        )

    def get_group_students(self, group_id: int, requester_id: int) -> Dict[str, Any]:
        """Get all students in group"""
        group = self.repos.group.get(group_id)
        if not group:
            return self._format_error_response("Group not found")

        # Permission check
        requester = self.repos.user.get(requester_id)
        if not requester:
            return self._format_error_response("Invalid requester")

        can_view = (
                requester.has_role(UserRole.SUPER_ADMIN) or
                (requester.learning_center_id == group.branch.learning_center_id and
                 requester.has_any_role([UserRole.ADMIN, UserRole.GROUP_MANAGER, UserRole.TEACHER, UserRole.RECEPTION]))
        )

        if not can_view:
            return self._format_error_response("Insufficient permissions")

        students = self.repos.group.get_group_students(group_id)

        from app.schemas import UserResponse
        students_data = [UserResponse.from_orm(student) for student in students]

        response = GroupStudentsList(
            group_id=group_id,
            students=students_data,
            total_students=len(students_data)
        )

        return self._format_success_response(response)

    def transfer_student(self, user_id: int, from_group_id: int, to_group_id: int, requester_id: int) -> Dict[str, Any]:
        """Transfer student from one group to another"""
        # Verify both groups exist and are in same learning center
        from_group = self.repos.group.get(from_group_id)
        to_group = self.repos.group.get(to_group_id)

        if not from_group or not to_group:
            return self._format_error_response("One or both groups not found")

        if from_group.branch.learning_center_id != to_group.branch.learning_center_id:
            return self._format_error_response("Cannot transfer between different learning centers")

        # Permission check
        if not self._check_permissions(requester_id, [UserRole.GROUP_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       from_group.branch.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        # Verify student
        student = self.repos.user.get(user_id)
        if not student or not student.has_role(UserRole.STUDENT):
            return self._format_error_response("Student not found")

        # Transfer student
        success = self.repos.group.transfer_student(user_id, from_group_id, to_group_id)

        if not success:
            return self._format_error_response("Failed to transfer student")

        return self._format_success_response({
            "from_group": GroupResponse.from_orm(from_group),
            "to_group": GroupResponse.from_orm(to_group),
            "student_name": student.full_name
        }, f"Student {student.full_name} transferred successfully")

    def assign_teacher(self, group_id: int, teacher_id: int, assigner_id: int) -> Dict[str, Any]:
        """Assign teacher to group"""
        group = self.repos.group.get(group_id)
        if not group:
            return self._format_error_response("Group not found")

        # Permission check
        if not self._check_permissions(assigner_id, [UserRole.GROUP_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       group.branch.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        # Assign teacher
        updated_group = self.repos.group.assign_teacher(group_id, teacher_id)

        if not updated_group:
            return self._format_error_response("Failed to assign teacher. Check if teacher exists and has correct role")

        return self._format_success_response(
            GroupResponse.from_orm(updated_group),
            "Teacher assigned successfully"
        )

    def remove_teacher(self, group_id: int, remover_id: int) -> Dict[str, Any]:
        """Remove teacher from group"""
        group = self.repos.group.get(group_id)
        if not group:
            return self._format_error_response("Group not found")

        # Permission check
        if not self._check_permissions(remover_id, [UserRole.GROUP_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       group.branch.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        updated_group = self.repos.group.remove_teacher(group_id)

        return self._format_success_response(
            GroupResponse.from_orm(updated_group),
            "Teacher removed from group successfully"
        )

    def search_groups(self, query: str, learning_center_id: int, requester_id: int) -> Dict[str, Any]:
        """Search groups by title"""
        if not self._check_permissions(requester_id, [UserRole.GROUP_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN,
                                                      UserRole.RECEPTION], learning_center_id):
            return self._format_error_response("Insufficient permissions")

        groups = self.repos.group.search_groups(learning_center_id, query)
        groups_data = [GroupResponse.from_orm(group) for group in groups]

        return self._format_success_response(groups_data)

    def get_groups_needing_teacher(self, learning_center_id: int, requester_id: int) -> Dict[str, Any]:
        """Get active groups without assigned teacher"""
        if not self._check_permissions(requester_id, [UserRole.GROUP_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       learning_center_id):
            return self._format_error_response("Insufficient permissions")

        groups = self.repos.group.get_groups_needing_teacher(learning_center_id)
        groups_data = [GroupResponse.from_orm(group) for group in groups]

        return self._format_success_response(groups_data, f"Found {len(groups_data)} groups without teacher")

    def get_group_capacity_info(self, group_id: int, requester_id: int) -> Dict[str, Any]:
        """Get group capacity information"""
        group = self.repos.group.get(group_id)
        if not group:
            return self._format_error_response("Group not found")

        # Permission check
        if not self._check_permissions(requester_id, [UserRole.GROUP_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN,
                                                      UserRole.RECEPTION], group.branch.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        capacity_info = self.repos.group.get_group_capacity_info(group_id)

        return self._format_success_response(capacity_info)

    def get_student_groups(self, user_id: int, requester_id: int) -> Dict[str, Any]:
        """Get all groups a student belongs to"""
        student = self.repos.user.get(user_id)
        if not student or not student.has_role(UserRole.STUDENT):
            return self._format_error_response("Student not found")

        # Permission check
        can_view = (
                user_id == requester_id or  # Student viewing own groups
                self._check_permissions(requester_id, [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.GROUP_MANAGER,
                                                       UserRole.TEACHER], student.learning_center_id)
        )

        if not can_view:
            return self._format_error_response("Insufficient permissions")

        groups = self.repos.group.get_student_groups(user_id)
        groups_data = [GroupResponse.from_orm(group) for group in groups]

        return self._format_success_response(groups_data)
from enum import Enum
from typing import Dict, List


class UserRole(str, Enum):
    # Top level
    SUPER_ADMIN = "super_admin"

    # Learning center management
    CEO = "ceo"  # Learning center CEO/Admin

    # Staff roles (created by CEO)
    RECEPTION = "reception"
    CONTENT_MANAGER = "content_manager"
    GROUP_MANAGER = "group_manager"

    # Students and parents
    STUDENT = "student"
    PARENT = "parent"


# Role hierarchy and permissions
ROLE_HIERARCHY: Dict[str, List[str]] = {
    UserRole.SUPER_ADMIN: [
        UserRole.CEO,
        UserRole.RECEPTION,
        UserRole.CONTENT_MANAGER,
        UserRole.GROUP_MANAGER,
        UserRole.STUDENT,
        UserRole.PARENT
    ],
    UserRole.CEO: [
        UserRole.RECEPTION,
        UserRole.CONTENT_MANAGER,
        UserRole.GROUP_MANAGER,
        UserRole.STUDENT,
        UserRole.PARENT
    ],
    UserRole.RECEPTION: [UserRole.STUDENT, UserRole.PARENT],
    UserRole.CONTENT_MANAGER: [],
    UserRole.GROUP_MANAGER: [UserRole.STUDENT],
    UserRole.STUDENT: [],
    UserRole.PARENT: []
}

# Role permissions mapping
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    UserRole.SUPER_ADMIN: [
        "manage_ceos",
        "view_all_data",
        "system_settings"
    ],
    UserRole.CEO: [
        "create_staff",
        "manage_reception",
        "manage_content_managers",
        "manage_group_managers",
        "view_center_data",
        "view_analytics"
    ],
    UserRole.RECEPTION: [
        "create_parents",
        "create_students",
        "manage_parents",
        "manage_students",
        "view_student_progress"
    ],
    UserRole.CONTENT_MANAGER: [
        "create_modules",
        "manage_modules",
        "create_lessons",
        "manage_lessons",
        "create_words",
        "manage_words",
        "view_content_analytics"
    ],
    UserRole.GROUP_MANAGER: [
        "create_groups",
        "manage_groups",
        "add_students_to_groups",
        "remove_students_from_groups",
        "view_group_progress",
        "manage_group_schedule"
    ],
    UserRole.STUDENT: [
        "view_own_progress",
        "access_lessons",
        "take_quizzes",
        "view_leaderboard",
        "view_badges",
        "view_weeklist"
    ],
    UserRole.PARENT: [
        "view_child_progress",
        "view_child_schedule",
        "communicate_with_staff"
    ]
}


def can_manage_role(manager_role: str, target_role: str) -> bool:
    """Check if a role can manage another role"""
    return target_role in ROLE_HIERARCHY.get(manager_role, [])


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission"""
    return permission in ROLE_PERMISSIONS.get(role, [])


def get_manageable_roles(role: str) -> List[str]:
    """Get list of roles that this role can manage"""
    return ROLE_HIERARCHY.get(role, [])
# Import all schemas for easy access
from .base import (
    BaseSchema,
    TimestampMixin,
    PaginationParams,
    PaginatedResponse,
    SuccessResponse,
    ErrorResponse,
    PhoneNumberMixin,
    NameMixin,
    SearchParams,
    FilterParams,
    SortParams
)

# User schemas
from .user import (
    UserRole,
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserWithDetails,
    UserCenterRoleBase,
    UserCenterRoleCreate,
    UserCenterRoleUpdate,
    UserCenterRoleResponse,
    LoginRequest,
    LoginResponse,
    UserStats,
    BulkUserCreate,
    UserSearchRequest,
    ChangeRoleRequest,
    RoleChangeResponse
)

# Learning center & business schemas
from .learning_center import (
    LearningCenterBase,
    LearningCenterCreate,
    LearningCenterUpdate,
    LearningCenterResponse,
    LearningCenterWithStats,
    BranchBase,
    BranchCreate,
    BranchUpdate,
    BranchResponse,
    BranchWithStats,
    PaymentBase,
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    LocationQuery,
    NearbyBranchResponse,
    LearningCenterAnalytics,
    SubscriptionAlert
)

# Content schemas
from .content import (
    CourseLevel,
    CourseBase,
    CourseCreate,
    CourseUpdate,
    CourseResponse,
    ModuleBase,
    ModuleCreate,
    ModuleUpdate,
    ModuleResponse,
    LessonBase,
    LessonCreate,
    LessonUpdate,
    LessonResponse,
    WordBase,
    WordCreate,
    WordUpdate,
    WordResponse,
    # Nested schemas
    WordInLesson,
    LessonWithWords,
    LessonInModule,
    ModuleWithLessons,
    ModuleWithFullContent,
    ModuleInCourse,
    CourseWithModules,
    CourseWithFullContent,
    # Bulk operations
    WordBulkCreate,
    WordBulkUpdate,
    WordImportRequest,
    # Search
    ContentSearchRequest,
    WordSearchRequest,
    ContentStatistics
)

# Learning & progress schemas
from .learning import (
    WordStrength,
    ProgressBase,
    ProgressCreate,
    ProgressUpdate,
    ProgressResponse,
    QuizSessionBase,
    QuizSessionCreate,
    QuizSessionUpdate,
    QuizSessionResponse,
    QuizSubmission,
    QuizResult,
    WeakWordBase,
    WeakWordCreate,
    WeakWordUpdate,
    WeakWordResponse,
    WeakWordWithDetails,
    UserLearningStats,
    LessonStats,
    PracticeRequest,
    PracticeSession
)

# Gamification schemas (leaderboard only)
from .gamification import (
    LeaderboardType,
    LeaderboardEntryBase,
    LeaderboardEntryCreate,
    LeaderboardEntryUpdate,
    LeaderboardEntryResponse,
    LeaderboardQuery,
    LeaderboardResponse,
    GameStats,
    LeaderboardUpdateRequest,
    LeaderboardAnalytics,
    UserLeaderboardSummary
)

# Group schemas
from .group import (
    GroupBase,
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupWithDetails,
    StudentGroupAssignment,
    StudentGroupBulkAssignment,
    StudentGroupRemoval,
    StudentGroupTransfer,
    GroupStudentsList,
    GroupsList,
    TeacherAssignment,
    TeacherRemoval,
    GroupSearchRequest,
    GroupAnalytics,
    GroupCapacityInfo,
    BulkGroupUpdate,
    GroupCreationBatch
)

# Verification schemas
from .verification import (
    VerificationCodeBase,
    VerificationCodeCreate,
    VerificationCodeResponse,
    SendVerificationRequest,
    SendVerificationResponse,
    VerifyCodeRequest,
    VerifyCodeResponse,
    ResendCodeRequest,
    VerificationStatusRequest,
    VerificationStatusResponse,
    VerificationAnalytics,
    VerificationCleanupRequest,
    VerificationCleanupResponse,
    RateLimitStatus,
    PhoneValidationRequest,
    PhoneValidationResponse
)

__all__ = [
    # Base
    "BaseSchema",
    "TimestampMixin",
    "PaginationParams",
    "PaginatedResponse",
    "SuccessResponse",
    "ErrorResponse",
    "PhoneNumberMixin",
    "NameMixin",
    "SearchParams",
    "FilterParams",
    "SortParams",

    # User
    "UserRole",
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserWithDetails",
    "UserCenterRoleBase",
    "UserCenterRoleCreate",
    "UserCenterRoleUpdate",
    "UserCenterRoleResponse",
    "LoginRequest",
    "LoginResponse",
    "UserStats",
    "BulkUserCreate",
    "UserSearchRequest",
    "ChangeRoleRequest",
    "RoleChangeResponse",

    # Learning center & business
    "LearningCenterBase",
    "LearningCenterCreate",
    "LearningCenterUpdate",
    "LearningCenterResponse",
    "LearningCenterWithStats",
    "BranchBase",
    "BranchCreate",
    "BranchUpdate",
    "BranchResponse",
    "BranchWithStats",
    "PaymentBase",
    "PaymentCreate",
    "PaymentUpdate",
    "PaymentResponse",
    "LocationQuery",
    "NearbyBranchResponse",
    "LearningCenterAnalytics",
    "SubscriptionAlert",

    # Content
    "CourseLevel",
    "CourseBase",
    "CourseCreate",
    "CourseUpdate",
    "CourseResponse",
    "ModuleBase",
    "ModuleCreate",
    "ModuleUpdate",
    "ModuleResponse",
    "LessonBase",
    "LessonCreate",
    "LessonUpdate",
    "LessonResponse",
    "WordBase",
    "WordCreate",
    "WordUpdate",
    "WordResponse",
    # Nested
    "WordInLesson",
    "LessonWithWords",
    "LessonInModule",
    "ModuleWithLessons",
    "ModuleWithFullContent",
    "ModuleInCourse",
    "CourseWithModules",
    "CourseWithFullContent",
    # Bulk
    "WordBulkCreate",
    "WordBulkUpdate",
    "WordImportRequest",
    # Search
    "ContentSearchRequest",
    "WordSearchRequest",
    "ContentStatistics",

    # Learning & progress
    "WordStrength",
    "ProgressBase",
    "ProgressCreate",
    "ProgressUpdate",
    "ProgressResponse",
    "QuizSessionBase",
    "QuizSessionCreate",
    "QuizSessionUpdate",
    "QuizSessionResponse",
    "QuizSubmission",
    "QuizResult",
    "WeakWordBase",
    "WeakWordCreate",
    "WeakWordUpdate",
    "WeakWordResponse",
    "WeakWordWithDetails",
    "UserLearningStats",
    "LessonStats",
    "PracticeRequest",
    "PracticeSession",

    # Gamification (leaderboard only)
    "LeaderboardType",
    "LeaderboardEntryBase",
    "LeaderboardEntryCreate",
    "LeaderboardEntryUpdate",
    "LeaderboardEntryResponse",
    "LeaderboardQuery",
    "LeaderboardResponse",
    "GameStats",
    "LeaderboardUpdateRequest",
    "LeaderboardAnalytics",
    "UserLeaderboardSummary",

    # Group
    "GroupBase",
    "GroupCreate",
    "GroupUpdate",
    "GroupResponse",
    "GroupWithDetails",
    "StudentGroupAssignment",
    "StudentGroupBulkAssignment",
    "StudentGroupRemoval",
    "StudentGroupTransfer",
    "GroupStudentsList",
    "GroupsList",
    "TeacherAssignment",
    "TeacherRemoval",
    "GroupSearchRequest",
    "GroupAnalytics",
    "GroupCapacityInfo",
    "BulkGroupUpdate",
    "GroupCreationBatch",

    # Verification
    "VerificationCodeBase",
    "VerificationCodeCreate",
    "VerificationCodeResponse",
    "SendVerificationRequest",
    "SendVerificationResponse",
    "VerifyCodeRequest",
    "VerifyCodeResponse",
    "ResendCodeRequest",
    "VerificationStatusRequest",
    "VerificationStatusResponse",
    "VerificationAnalytics",
    "VerificationCleanupRequest",
    "VerificationCleanupResponse",
    "RateLimitStatus",
    "PhoneValidationRequest",
    "PhoneValidationResponse"
]


# Schema groupings for easy imports
USER_SCHEMAS = [
    UserRole, UserBase, UserCreate, UserUpdate, UserResponse, UserWithDetails,
    LoginRequest, LoginResponse, UserStats
]

LEARNING_CENTER_SCHEMAS = [
    LearningCenterBase, LearningCenterCreate, LearningCenterUpdate, LearningCenterResponse,
    BranchBase, BranchCreate, BranchUpdate, BranchResponse,
    PaymentBase, PaymentCreate, PaymentResponse
]

CONTENT_SCHEMAS = [
    CourseBase, CourseCreate, CourseUpdate, CourseResponse,
    ModuleBase, ModuleCreate, ModuleUpdate, ModuleResponse,
    LessonBase, LessonCreate, LessonUpdate, LessonResponse,
    WordBase, WordCreate, WordUpdate, WordResponse
]

LEARNING_SCHEMAS = [
    ProgressBase, ProgressCreate, ProgressUpdate, ProgressResponse,
    QuizSessionBase, QuizSessionCreate, QuizSessionResponse,
    WeakWordBase, WeakWordCreate, WeakWordResponse
]

GAMIFICATION_SCHEMAS = [
    LeaderboardEntryBase, LeaderboardEntryCreate, LeaderboardEntryResponse,
    LeaderboardQuery, LeaderboardResponse
]

GROUP_SCHEMAS = [
    GroupBase, GroupCreate, GroupUpdate, GroupResponse, GroupWithDetails,
    StudentGroupAssignment, StudentGroupBulkAssignment
]

VERIFICATION_SCHEMAS = [
    SendVerificationRequest, SendVerificationResponse,
    VerifyCodeRequest, VerifyCodeResponse,
    VerificationStatusRequest, VerificationStatusResponse
]

# Common response schemas
COMMON_RESPONSES = [
    SuccessResponse, ErrorResponse, PaginatedResponse
]

# For backwards compatibility and easy usage
def get_schemas_by_domain(domain: str) -> list:
    """Get all schemas for a specific domain"""
    schema_map = {
        "user": USER_SCHEMAS,
        "learning_center": LEARNING_CENTER_SCHEMAS,
        "content": CONTENT_SCHEMAS,
        "learning": LEARNING_SCHEMAS,
        "gamification": GAMIFICATION_SCHEMAS,
        "group": GROUP_SCHEMAS,
        "verification": VERIFICATION_SCHEMAS,
        "common": COMMON_RESPONSES
    }
    return schema_map.get(domain.lower(), [])


# Type hints for common schema patterns
from typing import Union

UserSchemaTypes = Union[UserCreate, UserUpdate, UserResponse]
ContentSchemaTypes = Union[CourseCreate, ModuleCreate, LessonCreate, WordCreate]
LearningSchemaTypes = Union[ProgressCreate, QuizSessionCreate, WeakWordCreate]
ResponseSchemaTypes = Union[SuccessResponse, ErrorResponse, PaginatedResponse]
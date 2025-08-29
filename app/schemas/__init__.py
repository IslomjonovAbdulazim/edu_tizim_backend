# Import all schemas for easy access
from .base import BaseSchema, TimestampMixin, PaginationParams, PaginatedResponse

# User schemas
from .user import (
    UserRole, UserBase, UserCreate, UserUpdate, UserResponse, UserWithDetails,
    LoginRequest, LoginResponse, UserStats
)

# Learning center & business schemas
from .learning_center import (
    LearningCenterBase, LearningCenterCreate, LearningCenterUpdate, LearningCenterResponse,
    LearningCenterWithStats, BranchBase, BranchCreate, BranchUpdate, BranchResponse,
    BranchWithStats, PaymentBase, PaymentCreate, PaymentResponse
)

# Content schemas
from .content import (
    CourseBase, CourseCreate, CourseUpdate, CourseResponse, CourseWithModules, CourseWithFullContent,
    ModuleBase, ModuleCreate, ModuleUpdate, ModuleResponse, ModuleWithLessons, ModuleWithFullContent,
    LessonBase, LessonCreate, LessonUpdate, LessonResponse, LessonWithWords,
    WordBase, WordCreate, WordUpdate, WordResponse, WordBulkCreate, WordBulkUpdate
)

# Learning & progress schemas
from .learning import (
    ProgressBase, ProgressCreate, ProgressUpdate, ProgressResponse,
    QuizSessionBase, QuizSessionCreate, QuizSessionUpdate, QuizSessionResponse,
    QuizSubmission, QuizResult,
    WeakWordBase, WeakWordCreate, WeakWordUpdate, WeakWordResponse, WeakWordWithDetails,
    UserLearningStats, LessonStats
)

# Gamification schemas
from .gamification import (
    LeaderboardType, BadgeCategory,
    LeaderboardEntryBase, LeaderboardEntryCreate, LeaderboardEntryResponse,
    UserBadgeBase, UserBadgeCreate, UserBadgeUpdate, UserBadgeResponse,
    LeaderboardQuery, LeaderboardResponse, BadgeProgress, UserBadgesSummary, GameStats
)

# Group schemas
from .group import (
    GroupBase, GroupCreate, GroupUpdate, GroupResponse, GroupWithDetails,
    StudentGroupAssignment, StudentGroupBulkAssignment, GroupStudentsList
)

# Verification schemas
from .verification import (
    VerificationCodeCreate, VerificationCodeResponse,
    SendVerificationRequest, SendVerificationResponse,
    VerifyCodeRequest, VerifyCodeResponse
)

__all__ = [
    # Base
    "BaseSchema", "TimestampMixin", "PaginationParams", "PaginatedResponse",

    # User
    "UserRole", "UserBase", "UserCreate", "UserUpdate", "UserResponse", "UserWithDetails",
    "LoginRequest", "LoginResponse", "UserStats",

    # Learning center & business
    "LearningCenterBase", "LearningCenterCreate", "LearningCenterUpdate", "LearningCenterResponse",
    "LearningCenterWithStats", "BranchBase", "BranchCreate", "BranchUpdate", "BranchResponse",
    "BranchWithStats", "PaymentBase", "PaymentCreate", "PaymentResponse",

    # Content
    "CourseBase", "CourseCreate", "CourseUpdate", "CourseResponse", "CourseWithModules",
    "CourseWithFullContent", "ModuleBase", "ModuleCreate", "ModuleUpdate", "ModuleResponse",
    "ModuleWithLessons", "ModuleWithFullContent", "LessonBase", "LessonCreate", "LessonUpdate",
    "LessonResponse", "LessonWithWords", "WordBase", "WordCreate", "WordUpdate", "WordResponse",
    "WordBulkCreate", "WordBulkUpdate",

    # Learning & progress
    "ProgressBase", "ProgressCreate", "ProgressUpdate", "ProgressResponse",
    "QuizSessionBase", "QuizSessionCreate", "QuizSessionUpdate", "QuizSessionResponse",
    "QuizSubmission", "QuizResult", "WeakWordBase", "WeakWordCreate", "WeakWordUpdate",
    "WeakWordResponse", "WeakWordWithDetails", "UserLearningStats", "LessonStats",

    # Gamification
    "LeaderboardType", "BadgeCategory", "LeaderboardEntryBase", "LeaderboardEntryCreate",
    "LeaderboardEntryResponse", "UserBadgeBase", "UserBadgeCreate", "UserBadgeUpdate",
    "UserBadgeResponse", "LeaderboardQuery", "LeaderboardResponse", "BadgeProgress",
    "UserBadgesSummary", "GameStats",

    # Group
    "GroupBase", "GroupCreate", "GroupUpdate", "GroupResponse", "GroupWithDetails",
    "StudentGroupAssignment", "StudentGroupBulkAssignment", "GroupStudentsList",

    # Verification
    "VerificationCodeCreate", "VerificationCodeResponse", "SendVerificationRequest",
    "SendVerificationResponse", "VerifyCodeRequest", "VerifyCodeResponse"
]
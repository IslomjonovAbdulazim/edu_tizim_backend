from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, BigInteger, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import date, timedelta
from app.models.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    # Core info
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False, index=True)
    telegram_id = Column(BigInteger, nullable=False, unique=True, index=True)
    role = Column(String(20), nullable=False, default="student")
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Learning center and branch
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    learning_center = relationship("LearningCenter", back_populates="users")
    branch = relationship("Branch", back_populates="users")

    # Role profiles (one-to-one)
    student_profile = relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")
    parent_profile = relationship("Parent", back_populates="user", uselist=False, cascade="all, delete-orphan")
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False, cascade="all, delete-orphan")

    # Learning data
    progress_records = relationship("Progress", back_populates="user", cascade="all, delete-orphan")
    user_badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
    weak_lists = relationship("WeakList", back_populates="user", cascade="all, delete-orphan")

    # Leaderboard relationships
    daily_leaderboard_entries = relationship("DailyLeaderboard", back_populates="user", cascade="all, delete-orphan")
    all_time_leaderboard_entries = relationship("AllTimeLeaderboard", back_populates="user",
                                                cascade="all, delete-orphan")
    group_leaderboard_entries = relationship("GroupLeaderboard", back_populates="user", cascade="all, delete-orphan")

    # Unique constraint
    __table_args__ = (
        UniqueConstraint('phone_number', 'learning_center_id', name='uq_user_phone_center'),
    )

    def __str__(self):
        return f"User({self.full_name}, {self.role})"

    @property
    def total_points(self):
        """Total points calculated from progress records"""
        return sum(progress.points for progress in self.progress_records if progress.points)

    @property
    def points_today(self):
        """Points earned today"""
        today = date.today()
        return sum(
            progress.points for progress in self.progress_records
            if progress.points and progress.updated_at.date() == today
        )

    @property
    def points_this_week(self):
        """Points earned this week"""
        week_start = date.today() - timedelta(days=date.today().weekday())
        return sum(
            progress.points for progress in self.progress_records
            if progress.points and progress.updated_at.date() >= week_start
        )

    @property
    def points_this_month(self):
        """Points earned this month"""
        today = date.today()
        month_start = today.replace(day=1)
        return sum(
            progress.points for progress in self.progress_records
            if progress.points and progress.updated_at.date() >= month_start
        )

    def has_role(self, role: str) -> bool:
        """Check if user has specific role"""
        return self.role.lower() == role.lower()

    def has_any_role(self, roles: list) -> bool:
        """Check if user has any of the specified roles"""
        return self.role.lower() in [role.lower() for role in roles]

    def get_current_daily_rank(self, target_date: date = None) -> int:
        """Get user's current daily leaderboard rank"""
        if target_date is None:
            target_date = date.today()

        daily_entry = next(
            (entry for entry in self.daily_leaderboard_entries
             if entry.leaderboard_date == target_date), None
        )
        return daily_entry.rank if daily_entry else None

    def get_current_all_time_rank(self) -> int:
        """Get user's current all-time leaderboard rank"""
        all_time_entry = next(
            (entry for entry in self.all_time_leaderboard_entries), None
        )
        return all_time_entry.rank if all_time_entry else None

    def get_group_ranks(self, leaderboard_type: str = "daily", target_date: date = None):
        """Get user's ranks across all groups they belong to"""
        if target_date is None and leaderboard_type == "daily":
            target_date = date.today()

        group_ranks = []
        for entry in self.group_leaderboard_entries:
            if entry.leaderboard_type.value == leaderboard_type:
                if leaderboard_type == "daily" and entry.leaderboard_date == target_date:
                    group_ranks.append({
                        'group_name': entry.group_name,
                        'rank': entry.rank,
                        'points': entry.points
                    })
                elif leaderboard_type == "all_time":
                    group_ranks.append({
                        'group_name': entry.group_name,
                        'rank': entry.rank,
                        'points': entry.points
                    })

        return group_ranks
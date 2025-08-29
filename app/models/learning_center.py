from sqlalchemy import Column, String, Boolean, Text, Integer, Date, Numeric, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from datetime import datetime, date, timedelta


class LearningCenter(BaseModel):
    __tablename__ = "learning_centers"

    # Basic info
    name = Column(String(100), nullable=False)
    description = Column(Text)

    # Contact info
    main_phone = Column(String(20))
    website = Column(String(200))

    # Settings
    is_active = Column(Boolean, default=False, nullable=False)  # Default False until first payment

    # Branding
    logo_url = Column(String(500))

    # Registration phone (for login)
    registration_number = Column(String(50))

    # Limits
    max_branches = Column(Integer, default=5)
    max_students = Column(Integer, default=1000)

    # Payment & Subscription Management
    remaining_days = Column(Integer, default=0, nullable=False)  # Days of service left
    expires_at = Column(Date)  # When service expires (calculated from remaining_days)
    last_payment_date = Column(Date)  # Last payment received
    total_paid = Column(Numeric(10, 2), default=0.00)  # Lifetime payment amount

    # Relationships
    users = relationship("User", back_populates="learning_center", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="learning_center", cascade="all, delete-orphan")
    branches = relationship("Branch", back_populates="learning_center", cascade="all, delete-orphan")

    # Leaderboard relationships
    daily_leaderboards = relationship("DailyLeaderboard", back_populates="learning_center",
                                      cascade="all, delete-orphan")
    all_time_leaderboards = relationship("AllTimeLeaderboard", back_populates="learning_center",
                                         cascade="all, delete-orphan")

    payments = relationship("Payment", back_populates="learning_center", cascade="all, delete-orphan")

    def __str__(self):
        return f"LearningCenter({self.name})"

    @property
    def is_expired(self):
        """Check if learning center subscription has expired"""
        if not self.expires_at:
            return False
        return date.today() > self.expires_at

    @property
    def days_until_expiry(self):
        """Days remaining until expiry"""
        if not self.expires_at:
            return 0
        delta = self.expires_at - date.today()
        return max(0, delta.days)

    @property
    def is_expiring_soon(self):
        """Check if expiring within 7 days"""
        return 0 < self.days_until_expiry <= 7

    @property
    def total_users(self):
        """Get total number of users"""
        return len(self.users)

    @property
    def active_users(self):
        """Get number of active users"""
        return len([user for user in self.users if user.is_active])

    @property
    def total_courses(self):
        """Get total number of courses"""
        return len(self.courses)

    @property
    def active_courses(self):
        """Get number of active courses"""
        return len([course for course in self.courses if course.is_active])

    @property
    def total_branches(self):
        """Get total number of branches"""
        return len(self.branches)

    @property
    def active_branches(self):
        """Get number of active branches"""
        return len([branch for branch in self.branches if branch.is_active])

    def get_leaderboard_stats(self, target_date: date = None):
        """Get leaderboard statistics for this center"""
        if target_date is None:
            target_date = date.today()

        # Daily leaderboard stats
        daily_entries = [
            entry for entry in self.daily_leaderboards
            if entry.leaderboard_date == target_date
        ]

        # All-time leaderboard stats
        all_time_entries = self.all_time_leaderboards

        return {
            'daily': {
                'date': target_date,
                'participants': len(daily_entries),
                'top_performer': daily_entries[0].user_full_name if daily_entries else None,
                'top_points': daily_entries[0].points if daily_entries else 0
            },
            'all_time': {
                'participants': len(all_time_entries),
                'top_performer': all_time_entries[0].user_full_name if all_time_entries else None,
                'top_points': all_time_entries[0].total_points if all_time_entries else 0
            }
        }
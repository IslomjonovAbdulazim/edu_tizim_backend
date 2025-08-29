from sqlalchemy import Column, String, Boolean, Time, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class LearningCenter(BaseModel):
    __tablename__ = "learning_centers"

    # Basic information
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Regional settings
    country_code = Column(String(10), nullable=False, default="uz")  # ISO country code
    timezone = Column(String(50), nullable=False, default="Asia/Tashkent")

    # Main contact information (headquarters)
    main_phone = Column(String(20), nullable=True)
    main_email = Column(String(100), nullable=True)
    website = Column(String(200), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # System settings
    leaderboard_reset_time = Column(Time, nullable=False, default="00:00:00")

    # Branding/customization
    logo_url = Column(String(500), nullable=True)
    brand_color = Column(String(7), nullable=True)  # Hex color code #FFFFFF

    # Business information
    registration_number = Column(String(50), nullable=True)  # Business registration
    tax_number = Column(String(50), nullable=True)

    # Relationships
    branches = relationship("Branch", back_populates="learning_center", cascade="all, delete-orphan",
                            order_by="Branch.name")
    users = relationship("User", back_populates="learning_center", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="learning_center", cascade="all, delete-orphan")
    daily_leaderboards = relationship("DailyLeaderboard", back_populates="learning_center",
                                      cascade="all, delete-orphan")

    def __str__(self):
        return f"LearningCenter(name='{self.name}', country='{self.country_code}')"

    @property
    def total_branches(self):
        """Get total number of branches"""
        return len(self.branches)

    @property
    def active_branches(self):
        """Get number of active branches"""
        return len([branch for branch in self.branches if branch.is_active])

    @property
    def total_groups(self):
        """Get total groups across all branches"""
        return sum(branch.total_groups for branch in self.branches if branch.is_active)

    @property
    def total_students(self):
        """Get total students across all branches"""
        return sum(branch.total_students for branch in self.branches if branch.is_active)

    @property
    def total_capacity(self):
        """Get total capacity across all branches"""
        return sum(branch.capacity or 0 for branch in self.branches if branch.is_active)

    @property
    def overall_utilization(self):
        """Get overall capacity utilization across all branches"""
        if not self.total_capacity:
            return 0.0
        return (self.total_students / self.total_capacity * 100) if self.total_capacity > 0 else 0.0

    def get_branch_by_code(self, code: str):
        """Get branch by code"""
        return next((branch for branch in self.branches if branch.code == code), None)

    def get_active_branches(self):
        """Get list of active branches"""
        return [branch for branch in self.branches if branch.is_active]
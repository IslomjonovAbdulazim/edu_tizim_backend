from sqlalchemy import Column, String, Boolean, Time, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class LearningCenter(BaseModel):
    __tablename__ = "learning_centers"

    # Basic info
    name = Column(String(100), nullable=False)
    description = Column(Text)

    # Location
    country_code = Column(String(10), nullable=False, default="uz")
    timezone = Column(String(50), nullable=False, default="Asia/Tashkent")

    # Contact info
    main_phone = Column(String(20))
    main_email = Column(String(100))
    website = Column(String(200))

    # Settings
    is_active = Column(Boolean, default=True, nullable=False)
    leaderboard_reset_time = Column(Time, default="00:00:00")

    # Branding
    logo_url = Column(String(500))
    brand_color = Column(String(7))  # Hex color

    # Business info
    registration_number = Column(String(50))
    tax_number = Column(String(50))

    # Relationships
    users = relationship("User", back_populates="learning_center", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="learning_center", cascade="all, delete-orphan")
    daily_leaderboards = relationship("DailyLeaderboard", back_populates="learning_center",
                                      cascade="all, delete-orphan")

    def __str__(self):
        return f"LearningCenter({self.name}, {self.country_code})"

    @property
    def total_users(self):
        return len(self.users)

    @property
    def active_users(self):
        return len([u for u in self.users if u.is_active])

    @property
    def total_courses(self):
        return len(self.courses)

    @property
    def active_courses(self):
        return len([c for c in self.courses if c.is_active])
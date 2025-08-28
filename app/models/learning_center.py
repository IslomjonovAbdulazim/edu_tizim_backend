from sqlalchemy import Column, String, Boolean, Time
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class LearningCenter(BaseModel):
    __tablename__ = "learning_centers"

    name = Column(String(100), nullable=False)
    location = Column(String(10), nullable=False, default="uz")  # Country code
    timezone = Column(String(50), nullable=False, default="Asia/Tashkent")
    phone_number = Column(String(20), nullable=True)
    address = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Daily leaderboard reset time (default 00:00)
    leaderboard_reset_time = Column(Time, nullable=False, default="00:00:00")

    # Relationships
    users = relationship("User", back_populates="learning_center", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="learning_center", cascade="all, delete-orphan")
    groups = relationship("Group", back_populates="learning_center", cascade="all, delete-orphan")
    daily_leaderboards = relationship("DailyLeaderboard", back_populates="learning_center",
                                      cascade="all, delete-orphan")

    def __str__(self):
        return f"LearningCenter(name='{self.name}', location='{self.location}')"
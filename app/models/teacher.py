from sqlalchemy import Column, String, Integer, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Teacher(BaseModel):
    __tablename__ = "teachers"

    # User link
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    user = relationship("User", back_populates="teacher_profile")

    # Teacher info
    subject_specialization = Column(String(100))
    teaching_experience_years = Column(Integer, default=0)
    qualification = Column(String(200))
    employment_type = Column(String(20), default="full_time")  # full_time, part_time
    hire_date = Column(Date)
    bio = Column(String(500))

    # Relationships
    groups = relationship("Group", back_populates="teacher")

    def __str__(self):
        return f"Teacher({self.user.full_name}, {self.subject_specialization})"

    @property
    def full_name(self):
        return self.user.full_name

    @property
    def phone_number(self):
        return self.user.phone_number

    @property
    def experience_level(self):
        """Experience level based on years"""
        years = self.teaching_experience_years or 0
        if years < 2:
            return "Beginner"
        elif years < 5:
            return "Intermediate"
        elif years < 10:
            return "Experienced"
        else:
            return "Expert"

    @property
    def active_groups_count(self):
        return len([g for g in self.groups if g.is_active])
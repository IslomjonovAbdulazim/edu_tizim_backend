from sqlalchemy import Column, String, Integer, ForeignKey, Date, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Teacher(BaseModel):
    __tablename__ = "teachers"

    # Link to user (must have GROUP_MANAGER role)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    user = relationship("User", back_populates="teacher_profile")

    # Teaching specific info
    subject_specialization = Column(String(100), nullable=True)  # English, Math, Science, etc.
    teaching_experience_years = Column(Integer, nullable=True, default=0)
    qualification = Column(String(200), nullable=True)  # TESOL, CELTA, Bachelor's in Education, etc.
    employment_type = Column(String(20), nullable=False, default="full_time")  # full_time, part_time, contract
    hire_date = Column(Date, nullable=True)

    # Additional info
    bio = Column(Text, nullable=True)  # Teacher biography
    notes = Column(String(500), nullable=True)  # Admin notes about teacher

    # Relationships
    groups = relationship("Group", back_populates="teacher")

    def __str__(self):
        return f"Teacher(user='{self.user.full_name}', subject='{self.subject_specialization}')"

    @property
    def full_name(self):
        return self.user.full_name

    @property
    def phone_number(self):
        return self.user.phone_number

    @property
    def is_active(self):
        return self.user.is_active

    @property
    def experience_level(self):
        """Get experience level based on years"""
        if not self.teaching_experience_years:
            return "New"
        elif self.teaching_experience_years < 2:
            return "Junior"
        elif self.teaching_experience_years < 5:
            return "Intermediate"
        elif self.teaching_experience_years < 10:
            return "Senior"
        else:
            return "Expert"

    @property
    def active_groups_count(self):
        """Count of active groups managed by this teacher"""
        return len([group for group in self.groups if group.is_active])

    def get_group_names(self):
        """Get list of group names managed by this teacher"""
        return [group.name for group in self.groups if group.is_active]
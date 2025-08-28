from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Time, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.models.student import student_group_association


class Group(BaseModel):
    __tablename__ = "groups"

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    max_capacity = Column(Integer, nullable=False, default=20)
    is_active = Column(Boolean, default=True, nullable=False)

    # Schedule information
    schedule_days = Column(String(20), nullable=True)  # e.g., "Mon,Wed,Fri"
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)

    # Learning Center relationship
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    learning_center = relationship("LearningCenter", back_populates="groups")

    # Course relationship
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    course = relationship("Course", back_populates="groups")

    # Group manager (staff member who manages this group)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    manager = relationship("User", foreign_keys=[manager_id])

    # Relationships
    students = relationship("Student", secondary=student_group_association, back_populates="groups")

    def __str__(self):
        return f"Group(name='{self.name}', course='{self.course.name}')"

    @property
    def current_capacity(self):
        return len(self.students)

    @property
    def available_spots(self):
        return self.max_capacity - self.current_capacity

    @property
    def is_full(self):
        return self.current_capacity >= self.max_capacity

    def can_add_student(self):
        return self.is_active and not self.is_full

    def get_student_names(self):
        """Get list of student names in this group"""
        return [student.full_name for student in self.students]
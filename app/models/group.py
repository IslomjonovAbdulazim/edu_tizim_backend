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

    # Branch relationship (groups belong to specific branches)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    branch = relationship("Branch", back_populates="groups")

    # Learning Center relationship (for backward compatibility and easier queries)
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    learning_center = relationship("LearningCenter")

    # Course relationship
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    course = relationship("Course", back_populates="groups")

    # Teacher relationship
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    teacher = relationship("Teacher", back_populates="groups")

    # Relationships
    students = relationship("Student", secondary=student_group_association, back_populates="groups")

    def __str__(self):
        branch_name = self.branch.name if self.branch else "No Branch"
        teacher_name = self.teacher.full_name if self.teacher else "No teacher"
        return f"Group(name='{self.name}', branch='{branch_name}', course='{self.course.name}', teacher='{teacher_name}')"

    @property
    def current_capacity(self):
        return len(self.students)

    @property
    def available_spots(self):
        return self.max_capacity - self.current_capacity

    @property
    def is_full(self):
        return self.current_capacity >= self.max_capacity

    @property
    def capacity_percentage(self):
        """Get capacity utilization as percentage"""
        return (self.current_capacity / self.max_capacity * 100) if self.max_capacity > 0 else 0

    def can_add_student(self):
        return self.is_active and not self.is_full

    def get_student_names(self):
        """Get list of student names in this group"""
        return [student.full_name for student in self.students]

    @property
    def teacher_name(self):
        """Get teacher name or default message"""
        return self.teacher.full_name if self.teacher else "No teacher assigned"

    @property
    def has_teacher(self):
        """Check if group has an assigned teacher"""
        return self.teacher is not None

    @property
    def branch_name(self):
        """Get branch name"""
        return self.branch.name if self.branch else "No branch"

    @property
    def branch_address(self):
        """Get branch address"""
        return self.branch.address if self.branch else "No address"

    @property
    def full_location(self):
        """Get full location info: Branch name"""
        return self.branch_name
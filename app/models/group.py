from sqlalchemy import Column, String, Integer, ForeignKey, Text, Index, CheckConstraint
from sqlalchemy.orm import relationship
from .base import BaseModel


class Group(BaseModel):
    __tablename__ = "groups"

    # Basic info with validation
    title = Column(String(100), nullable=False)
    schedule = Column(String(200))  # "Mon,Wed,Fri 10:00-12:00"
    description = Column(Text)

    # Relationships - clean and simple
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Derived learning center through branch relationship
    branch = relationship("Branch", back_populates="groups")
    course = relationship("Course")
    teacher = relationship("User", foreign_keys=[teacher_id])
    student_memberships = relationship("StudentGroup", back_populates="group", cascade="all, delete-orphan")
    leaderboard_entries = relationship("LeaderboardEntry", back_populates="group", cascade="all, delete-orphan")

    # For convenience - get learning center through branch
    @property
    def learning_center(self):
        return self.branch.learning_center if self.branch else None

    @property
    def learning_center_id(self):
        return self.branch.learning_center_id if self.branch else None

    # Constraints
    __table_args__ = (
        CheckConstraint("length(title) >= 2", name='chk_title_length'),
        Index('idx_branch_active', 'branch_id', 'is_active'),
        Index('idx_teacher_active', 'teacher_id', 'is_active'),
    )

    def __str__(self):
        return f"Group({self.title})"

    @property
    def active_students(self):
        """Get active students in this group"""
        return [m.user for m in self.student_memberships if m.is_active]

    @property
    def student_count(self):
        """Get count of active students"""
        return len([m for m in self.student_memberships if m.is_active])

    @property
    def teacher_name(self):
        return self.teacher.full_name if self.teacher else "No teacher assigned"
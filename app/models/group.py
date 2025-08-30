from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text, Index
from sqlalchemy.orm import relationship
from .base import BaseModel


class Group(BaseModel):
    __tablename__ = "groups"

    # Basic info
    title = Column(String(100), nullable=False)
    schedule = Column(String(200))  # "Mon,Wed,Fri 10:00-12:00"
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)

    # Related objects
    branch = relationship("Branch", back_populates="groups")
    course = relationship("Course")
    teacher = relationship("User", foreign_keys=[teacher_id], back_populates="teacher_groups")
    learning_center = relationship("LearningCenter", back_populates="groups")
    student_memberships = relationship("StudentGroup", back_populates="group", cascade="all, delete-orphan")
    leaderboard_entries = relationship("LeaderboardEntry", back_populates="group", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_branch_active', 'branch_id', 'is_active'),
        Index('idx_center_active', 'learning_center_id', 'is_active'),
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

    def add_student(self, user_id: int, added_by_id: int = None):
        """Add student to group"""
        # Check if already exists and active
        existing = next((m for m in self.student_memberships
                        if m.user_id == user_id and m.is_active), None)
        if existing:
            return False

        # Create new membership
        from .user import StudentGroup
        membership = StudentGroup(
            user_id=user_id,
            group_id=self.id,
            learning_center_id=self.learning_center_id,
            added_by_id=added_by_id
        )
        self.student_memberships.append(membership)
        return True

    def remove_student(self, user_id: int):
        """Remove student from group"""
        membership = next((m for m in self.student_memberships
                          if m.user_id == user_id and m.is_active), None)
        if membership:
            membership.is_active = False
            return True
        return False
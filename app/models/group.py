from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text, Table
from sqlalchemy.orm import relationship
from .base import BaseModel

# Many-to-many table for student-group relationship
student_groups = Table(
    'student_groups',
    BaseModel.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('groups.id'), primary_key=True)
)


class Group(BaseModel):
    __tablename__ = "groups"

    # Basic info
    title = Column(String(100), nullable=False)
    schedule = Column(String(200))  # "Mon,Wed,Fri 10:00-12:00" or flexible format
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)  # Optional course assignment
    teacher_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Teacher user

    # Related objects
    branch = relationship("Branch", back_populates="groups")
    course = relationship("Course")
    teacher = relationship("User", foreign_keys=[teacher_user_id])
    students = relationship("User", secondary=student_groups, backref="student_groups")
    leaderboard_entries = relationship("LeaderboardEntry", back_populates="group",
                                       cascade="all, delete-orphan")

    def __str__(self):
        return f"Group({self.title}, {self.branch.title})"

    @property
    def student_count(self):
        return len(self.students)

    @property
    def teacher_name(self):
        return self.teacher.full_name if self.teacher else "No teacher assigned"

    @property
    def learning_center(self):
        """Get the learning center this group belongs to"""
        return self.branch.learning_center if self.branch else None

    def can_user_access(self, user_id: int) -> bool:
        """Check if user can access this group (as student or teacher)"""
        # Check if user is the teacher
        if self.teacher_user_id == user_id:
            return True

        # Check if user is a student in this group
        return any(student.id == user_id for student in self.students)

    def add_student(self, user):
        """Add a student to the group"""
        if user not in self.students:
            self.students.append(user)

    def remove_student(self, user):
        """Remove a student from the group"""
        if user in self.students:
            self.students.remove(user)

    def get_active_students(self):
        """Get all active students in this group"""
        return [student for student in self.students if student.is_active]
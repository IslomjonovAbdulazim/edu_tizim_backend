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
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True)   # Teacher user

    # Related objects
    branch = relationship("Branch", back_populates="groups")
    course = relationship("Course")
    teacher = relationship("User", foreign_keys=[teacher_id])
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
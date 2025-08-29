from sqlalchemy import Column, String, Integer, ForeignKey, Date, Table
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

# Many-to-many association tables
student_groups = Table(
    'student_groups',
    BaseModel.metadata,
    Column('student_id', Integer, ForeignKey('students.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('groups.id'), primary_key=True)
)

parent_students = Table(
    'parent_students',
    BaseModel.metadata,
    Column('parent_id', Integer, ForeignKey('parents.id'), primary_key=True),
    Column('student_id', Integer, ForeignKey('students.id'), primary_key=True)
)

class Student(BaseModel):
    __tablename__ = "students"

    # User link
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    user = relationship("User", back_populates="student_profile")

    # Student info
    date_of_birth = Column(Date)
    grade_level = Column(String(20))  # "Grade 5", "Adult", etc.
    emergency_contact = Column(String(20))
    notes = Column(String(500))

    # Relationships
    groups = relationship("Group", secondary=student_groups, back_populates="students")
    parents = relationship("Parent", secondary=parent_students, back_populates="students")

    def __str__(self):
        return f"Student({self.user.full_name})"

    @property
    def full_name(self):
        return self.user.full_name

    @property
    def phone_number(self):
        return self.user.phone_number

    @property
    def total_points(self):
        return self.user.total_points
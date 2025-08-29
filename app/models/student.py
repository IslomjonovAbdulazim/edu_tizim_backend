from sqlalchemy import Column, String, Integer, ForeignKey, Date, Table
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

# Association table for many-to-many relationship between students and groups
student_group_association = Table(
    'student_groups',
    BaseModel.metadata,
    Column('student_id', Integer, ForeignKey('students.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('groups.id'), primary_key=True)
)

# Association table for parent-student relationships
parent_student_association = Table(
    'parent_students',
    BaseModel.metadata,
    Column('parent_id', Integer, ForeignKey('parents.id'), primary_key=True),
    Column('student_id', Integer, ForeignKey('students.id'), primary_key=True)
)


class Student(BaseModel):
    __tablename__ = "students"

    # Link to user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    user = relationship("User", back_populates="student_profile")

    # Student specific info
    date_of_birth = Column(Date, nullable=True)
    grade_level = Column(String(20), nullable=True)  # e.g., "Grade 5", "Adult", etc.
    emergency_contact = Column(String(20), nullable=True)
    notes = Column(String(500), nullable=True)  # Admin notes about student

    # Relationships
    groups = relationship("Group", secondary=student_group_association, back_populates="students")
    parents = relationship("Parent", secondary=parent_student_association, back_populates="students")

    def __str__(self):
        return f"Student(user='{self.user.full_name}')"

    @property
    def full_name(self):
        return self.user.full_name

    @property
    def phone_number(self):
        return self.user.phone_number

    @property
    def total_points(self):
        return self.user.total_points
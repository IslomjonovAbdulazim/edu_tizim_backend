from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class Group(Base):
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    learning_center = relationship("LearningCenter", back_populates="groups")
    course = relationship("Course", back_populates="groups")
    teacher = relationship("User", back_populates="groups_as_teacher", foreign_keys=[teacher_id])
    student_memberships = relationship("GroupStudent", back_populates="group")
    
    # Indexes
    __table_args__ = (
        Index("ix_group_learning_center", "learning_center_id"),
        Index("ix_group_teacher", "teacher_id"),
        Index("ix_group_course", "course_id"),
    )


class GroupStudent(Base):
    __tablename__ = "group_students"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=func.now())
    
    # Relationships
    group = relationship("Group", back_populates="student_memberships")
    student = relationship("User", back_populates="group_memberships")
    
    # Indexes
    __table_args__ = (
        Index("ix_group_student_group", "group_id"),
        Index("ix_group_student_student", "student_id"),
        Index("ix_group_student_unique", "group_id", "student_id", unique=True),
    )
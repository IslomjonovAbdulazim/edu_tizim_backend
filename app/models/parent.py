from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.models.student import parent_student_association


class Parent(BaseModel):
    __tablename__ = "parents"

    # Link to user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    user = relationship("User", back_populates="parent_profile")

    # Parent specific info
    occupation = Column(String(100), nullable=True)
    workplace = Column(String(100), nullable=True)
    relationship_to_student = Column(String(50), nullable=True)  # father, mother, guardian, etc.
    alternative_contact = Column(String(20), nullable=True)  # Alternative phone number
    notes = Column(String(500), nullable=True)  # Admin notes about parent

    # Relationships
    students = relationship("Student", secondary=parent_student_association, back_populates="parents")

    def __str__(self):
        return f"Parent(user='{self.user.full_name}', relationship='{self.relationship_to_student}')"

    @property
    def full_name(self):
        return self.user.full_name

    @property
    def phone_number(self):
        return self.user.phone_number

    def get_children_names(self):
        """Get list of children names"""
        return [student.full_name for student in self.students]
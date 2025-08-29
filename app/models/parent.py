from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.models.student import parent_students

class Parent(BaseModel):
    __tablename__ = "parents"

    # User link
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    user = relationship("User", back_populates="parent_profile")

    # Parent info
    occupation = Column(String(100))
    workplace = Column(String(100))
    relationship_to_student = Column(String(50))  # father, mother, guardian
    alternative_contact = Column(String(20))
    notes = Column(String(500))

    # Relationships
    students = relationship("Student", secondary=parent_students, back_populates="parents")

    def __str__(self):
        return f"Parent({self.user.full_name}, {self.relationship_to_student})"

    @property
    def full_name(self):
        return self.user.full_name

    @property
    def phone_number(self):
        return self.user.phone_number

    @property
    def children_names(self):
        """List of children names"""
        return [student.full_name for student in self.students]
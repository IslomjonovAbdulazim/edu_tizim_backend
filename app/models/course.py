from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Course(BaseModel):
    __tablename__ = "courses"

    # Basic info
    name = Column(String(100), nullable=False)
    description = Column(Text)
    level = Column(String(20), nullable=False, default="beginner")  # beginner, intermediate, advanced
    is_active = Column(Boolean, default=True, nullable=False)
    order_index = Column(Integer, default=0)

    # Learning center
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    learning_center = relationship("LearningCenter", back_populates="courses")

    # Relationships
    modules = relationship("Module", back_populates="course", cascade="all, delete-orphan", order_by="Module.order_index")
    groups = relationship("Group", back_populates="course", cascade="all, delete-orphan")

    def __str__(self):
        return f"Course({self.name}, {self.level})"

    @property
    def total_modules(self):
        return len(self.modules)

    @property
    def active_modules(self):
        return len([m for m in self.modules if m.is_active])

    @property
    def total_lessons(self):
        return sum(module.total_lessons for module in self.modules)

    @property
    def total_words(self):
        return sum(module.total_words for module in self.modules)

    @property
    def completion_points(self):
        """Total points for completing entire course"""
        return sum(module.completion_points for module in self.modules)
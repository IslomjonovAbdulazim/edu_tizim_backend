from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Course(BaseModel):
    __tablename__ = "courses"

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    language_from = Column(String(10), nullable=False, default="uz")  # Native language code
    language_to = Column(String(10), nullable=False, default="en")  # Target language code
    level = Column(String(20), nullable=False, default="beginner")  # beginner, intermediate, advanced
    is_active = Column(Boolean, default=True, nullable=False)
    order_index = Column(Integer, nullable=False, default=0)  # For ordering courses

    # Learning Center relationship
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    learning_center = relationship("LearningCenter", back_populates="courses")

    # Relationships
    modules = relationship("Module", back_populates="course", cascade="all, delete-orphan",
                           order_by="Module.order_index")
    groups = relationship("Group", back_populates="course")

    def __str__(self):
        return f"Course(name='{self.name}', level='{self.level}')"

    @property
    def total_modules(self):
        return len(self.modules)

    @property
    def total_lessons(self):
        return sum(len(module.lessons) for module in self.modules)

    @property
    def total_words(self):
        return sum(len(lesson.words) for module in self.modules for lesson in module.lessons)
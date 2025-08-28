from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Module(BaseModel):
    __tablename__ = "modules"

    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    order_index = Column(Integer, nullable=False, default=0)  # For ordering modules within course

    # Course relationship
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    course = relationship("Course", back_populates="modules")

    # Relationships
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan",
                           order_by="Lesson.order_index")

    def __str__(self):
        return f"Module(title='{self.title}', course='{self.course.name}')"

    @property
    def total_lessons(self):
        return len(self.lessons)

    @property
    def total_words(self):
        return sum(len(lesson.words) for lesson in self.lessons)

    @property
    def completion_points(self):
        """Total points available for completing this module"""
        return sum(lesson.completion_points for lesson in self.lessons)
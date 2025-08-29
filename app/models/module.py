from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Module(BaseModel):
    __tablename__ = "modules"

    # Basic info
    title = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    order_index = Column(Integer, default=0)

    # Course relationship
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    course = relationship("Course", back_populates="modules")

    # Relationships
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan", order_by="Lesson.order_index")

    def __str__(self):
        return f"Module({self.title}, {self.course.name})"

    @property
    def total_lessons(self):
        return len(self.lessons)

    @property
    def active_lessons(self):
        return len([l for l in self.lessons if l.is_active])

    @property
    def total_words(self):
        return sum(lesson.total_words for lesson in self.lessons)

    @property
    def completion_points(self):
        """Total points for completing module"""
        return sum(lesson.completion_points for lesson in self.lessons)
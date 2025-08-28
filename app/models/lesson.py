from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Lesson(BaseModel):
    __tablename__ = "lessons"

    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)  # Lesson content/instructions
    is_active = Column(Boolean, default=True, nullable=False)
    order_index = Column(Integer, nullable=False, default=0)  # For ordering lessons within module

    # Points system
    base_points = Column(Integer, nullable=False, default=50)  # Base points for lesson completion

    # Module relationship
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    module = relationship("Module", back_populates="lessons")

    # Relationships
    words = relationship("Word", back_populates="lesson", cascade="all, delete-orphan", order_by="Word.order_index")
    progress_records = relationship("Progress", back_populates="lesson", cascade="all, delete-orphan")

    def __str__(self):
        return f"Lesson(title='{self.title}', module='{self.module.title}')"

    @property
    def total_words(self):
        return len(self.words)

    @property
    def completion_points(self):
        """Calculate total points for 100% completion of this lesson"""
        word_points = self.total_words * 10  # 10 points per word
        return self.base_points + word_points

    @property
    def course(self):
        return self.module.course
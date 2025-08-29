from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Lesson(BaseModel):
    __tablename__ = "lessons"

    # Basic info
    title = Column(String(100), nullable=False)
    description = Column(Text)
    content = Column(Text)  # Lesson instructions
    is_active = Column(Boolean, default=True, nullable=False)
    order_index = Column(Integer, default=0)
    base_points = Column(Integer, default=50)

    # Module relationship
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    module = relationship("Module", back_populates="lessons")

    # Relationships
    words = relationship("Word", back_populates="lesson", cascade="all, delete-orphan", order_by="Word.order_index")
    progress_records = relationship("Progress", back_populates="lesson", cascade="all, delete-orphan")

    def __str__(self):
        return f"Lesson({self.title}, {self.module.title})"

    @property
    def total_words(self):
        return len(self.words)

    @property
    def completion_points(self):
        """Total points for completing lesson (base + word points)"""
        word_points = self.total_words * 10  # 10 points per word
        return self.base_points + word_points

    @property
    def course(self):
        return self.module.course
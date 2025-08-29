from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Word(BaseModel):
    __tablename__ = "words"

    # Word content
    foreign = Column(String(100), nullable=False)  # Target language (English)
    local = Column(String(100), nullable=False)    # Native language (Uzbek)
    example_sentence = Column(Text)
    audio_url = Column(String(255))

    # Metadata
    difficulty_level = Column(Integer, default=1)  # 1-5 scale
    word_type = Column(String(50))  # noun, verb, adjective, etc.
    is_active = Column(Boolean, default=True, nullable=False)
    order_index = Column(Integer, default=0)

    # Lesson relationship
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    lesson = relationship("Lesson", back_populates="words")

    def __str__(self):
        return f"Word({self.foreign} → {self.local})"

    @property
    def points_value(self):
        """Points for learning this word"""
        return 10

    @property
    def module(self):
        return self.lesson.module

    @property
    def course(self):
        return self.lesson.module.course
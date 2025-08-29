from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Word(BaseModel):
    __tablename__ = "words"

    foreign = Column(String(100), nullable=False)  # Word in foreign/target language (e.g., English)
    local = Column(String(100), nullable=False)  # Word in native/local language (e.g., Uzbek)
    example_sentence = Column(Text, nullable=True)  # Example sentence in foreign language
    audio_url = Column(String(255), nullable=True)  # URL to pronunciation audio file

    # Word metadata
    difficulty_level = Column(Integer, nullable=False, default=1)  # 1-5 scale
    word_type = Column(String(50), nullable=True)  # noun, verb, adjective, etc.
    is_active = Column(Boolean, default=True, nullable=False)
    order_index = Column(Integer, nullable=False, default=0)  # Order within lesson

    # Lesson relationship
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    lesson = relationship("Lesson", back_populates="words")

    def __str__(self):
        return f"Word(foreign='{self.foreign}', local='{self.local}')"

    @property
    def points_value(self):
        """Points awarded for learning this word"""
        return 10  # Base points per word

    @property
    def module(self):
        return self.lesson.module

    @property
    def course(self):
        return self.lesson.module.course

    @property
    def learning_center(self):
        return self.lesson.module.course.learning_center
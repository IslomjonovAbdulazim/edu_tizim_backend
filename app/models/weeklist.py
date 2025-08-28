from sqlalchemy import Column, Integer, ForeignKey, Date, Boolean, String
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class WeekList(BaseModel):
    __tablename__ = "week_lists"

    # User relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="weekly_lists")

    # Week information
    week_start_date = Column(Date, nullable=False)  # Monday of the week
    week_end_date = Column(Date, nullable=False)  # Sunday of the week
    is_active = Column(Boolean, default=True, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)

    # Algorithm context
    generation_context = Column(String(500), nullable=True)  # JSON string with algorithm details

    # Relationships
    words = relationship("WeekListWord", back_populates="week_list", cascade="all, delete-orphan")

    def __str__(self):
        return f"WeekList(user='{self.user.full_name}', week={self.week_start_date})"

    @property
    def total_words(self):
        return len(self.words)

    @property
    def completed_words(self):
        return len([w for w in self.words if w.is_mastered])

    @property
    def completion_percentage(self):
        if self.total_words == 0:
            return 0.0
        return (self.completed_words / self.total_words) * 100.0

    def mark_completed(self):
        """Mark week list as completed"""
        self.is_completed = True
        # This could trigger badge calculations


class WeekListWord(BaseModel):
    __tablename__ = "week_list_words"

    # Relationships
    week_list_id = Column(Integer, ForeignKey("week_lists.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)

    week_list = relationship("WeekList", back_populates="words")
    word = relationship("Word", back_populates="week_lists")

    # Progress tracking for this word in this week
    practice_count = Column(Integer, nullable=False, default=0)
    correct_count = Column(Integer, nullable=False, default=0)
    is_mastered = Column(Boolean, default=False, nullable=False)

    # Priority (for algorithm ordering)
    priority_score = Column(Integer, nullable=False, default=0)
    difficulty_multiplier = Column(Integer, nullable=False, default=1)

    def __str__(self):
        return f"WeekListWord(word='{self.word.foreign}', mastered={self.is_mastered})"

    @property
    def accuracy_percentage(self):
        if self.practice_count == 0:
            return 0.0
        return (self.correct_count / self.practice_count) * 100.0

    def record_practice(self, is_correct: bool):
        """Record a practice attempt for this word"""
        self.practice_count += 1
        if is_correct:
            self.correct_count += 1

        # Check if mastered (e.g., 80% accuracy with at least 5 attempts)
        if self.practice_count >= 5 and self.accuracy_percentage >= 80.0:
            self.is_mastered = True
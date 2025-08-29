from sqlalchemy import Column, Integer, ForeignKey, Boolean, DateTime, Text, func
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import json
from datetime import datetime
from typing import List, Dict, Any


class WeakList(BaseModel):
    __tablename__ = "weak_lists"

    # User
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="weak_lists")
    words = relationship("WeakListWord", back_populates="weak_list", cascade="all, delete-orphan")

    def __str__(self):
        return f"WeakList({self.user.full_name})"

    @property
    def total_words(self):
        return len([w for w in self.words if w.is_active])

    @property
    def words_needing_review(self):
        return len([w for w in self.words if w.is_active and w.needs_review])


class WeakListWord(BaseModel):
    __tablename__ = "weak_list_words"

    # Relationships
    weak_list_id = Column(Integer, ForeignKey("weak_lists.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)

    weak_list = relationship("WeakList", back_populates="words")
    word = relationship("Word")

    # Quiz performance tracking
    quiz_history = Column(Text, default="[]")  # JSON string of last 10 quiz results
    total_attempts = Column(Integer, default=0)
    correct_attempts = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    first_attempt_at = Column(DateTime)
    last_attempt_at = Column(DateTime)
    last_correct_at = Column(DateTime)

    def __str__(self):
        return f"WeakListWord({self.word.foreign} -> {self.word.local})"

    @property
    def accuracy_percentage(self):
        """Calculate accuracy percentage"""
        if self.total_attempts == 0:
            return 0.0
        return round((self.correct_attempts / self.total_attempts) * 100, 1)

    @property
    def recent_accuracy(self):
        """Calculate accuracy from last 5 attempts"""
        quiz_results = self.quiz_results
        if not quiz_results:
            return 0.0

        recent_results = quiz_results[-5:]  # Last 5 attempts
        correct = sum(1 for result in recent_results if result.get('is_correct', False))
        return round((correct / len(recent_results)) * 100, 1)

    @property
    def quiz_results(self) -> List[Dict[str, Any]]:
        """Get quiz results as list of dictionaries"""
        try:
            return json.loads(self.quiz_history or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    @property
    def performance_level(self) -> str:
        """Determine performance level based on accuracy and attempts"""
        if self.total_attempts < 3:
            return "new"

        accuracy = self.accuracy_percentage
        recent_accuracy = self.recent_accuracy

        # Use recent accuracy if available, otherwise overall accuracy
        current_accuracy = recent_accuracy if len(self.quiz_results) >= 3 else accuracy

        if current_accuracy >= 85:
            return "excellent"
        elif current_accuracy >= 70:
            return "good"
        elif current_accuracy >= 50:
            return "weak"
        else:
            return "critical"

    @property
    def needs_review(self) -> bool:
        """Check if word needs review"""
        if self.total_attempts < 2:
            return False

        # If recent accuracy is low or has mistake pattern
        if self.recent_accuracy < 60:
            return True

        # If not practiced recently (more than 7 days)
        if self.last_attempt_at:
            days_since_last = (datetime.utcnow() - self.last_attempt_at).days
            if days_since_last > 7 and self.accuracy_percentage < 80:
                return True

        return False

    @property
    def is_mastered(self) -> bool:
        """Check if word is mastered"""
        if self.total_attempts < 5:
            return False

        return (self.accuracy_percentage >= 90 and
                self.recent_accuracy >= 85 and
                self.total_attempts >= 5)

    def record_quiz_attempt(self, is_correct: bool, quiz_type: str = "multiple_choice",
                            response_time_ms: int = None):
        """Record a new quiz attempt"""
        now = datetime.utcnow()

        # Update attempt counts
        self.total_attempts += 1
        if is_correct:
            self.correct_attempts += 1
            self.last_correct_at = now

        # Update timestamps
        if not self.first_attempt_at:
            self.first_attempt_at = now
        self.last_attempt_at = now

        # Add to quiz history (keep last 10)
        quiz_results = self.quiz_results
        new_result = {
            "is_correct": is_correct,
            "quiz_type": quiz_type,
            "timestamp": now.isoformat(),
            "response_time_ms": response_time_ms
        }

        quiz_results.append(new_result)

        # Keep only last 10 results
        if len(quiz_results) > 10:
            quiz_results = quiz_results[-10:]

        self.quiz_history = json.dumps(quiz_results)

    def get_mistake_pattern(self) -> Dict[str, Any]:
        """Analyze mistake patterns"""
        quiz_results = self.quiz_results
        if not quiz_results:
            return {"mistake_streak": 0, "common_errors": []}

        # Calculate current mistake streak
        mistake_streak = 0
        for result in reversed(quiz_results):
            if not result.get('is_correct', False):
                mistake_streak += 1
            else:
                break

        # Count error types
        error_types = {}
        for result in quiz_results:
            if not result.get('is_correct', False):
                quiz_type = result.get('quiz_type', 'unknown')
                error_types[quiz_type] = error_types.get(quiz_type, 0) + 1

        return {
            "mistake_streak": mistake_streak,
            "common_errors": error_types,
            "total_mistakes": len([r for r in quiz_results if not r.get('is_correct', False)])
        }
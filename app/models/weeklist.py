from sqlalchemy import Column, Integer, ForeignKey, Boolean, String, DateTime, func
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import json
from datetime import datetime


class WeakList(BaseModel):
    __tablename__ = "weak_lists"

    # User relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="weak_list")

    # Metadata
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    words = relationship("WeakListWord", back_populates="weak_list", cascade="all, delete-orphan")

    def __str__(self):
        return f"WeakList(user='{self.user.full_name}', words={self.total_words})"

    @property
    def total_words(self):
        return len(self.words)

    @property
    def weak_words_count(self):
        """Count of words with accuracy < 70%"""
        return len([w for w in self.words if w.accuracy_percentage < 70.0])

    @property
    def strong_words_count(self):
        """Count of words with accuracy >= 80%"""
        return len([w for w in self.words if w.accuracy_percentage >= 80.0])

    @property
    def needs_review_count(self):
        """Count of words that need review (accuracy < 60% or recent mistakes)"""
        return len([w for w in self.words if w.needs_review])


class WeakListWord(BaseModel):
    __tablename__ = "weak_list_words"

    # Relationships
    weak_list_id = Column(Integer, ForeignKey("weak_lists.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)

    weak_list = relationship("WeakList", back_populates="words")
    word = relationship("Word")

    # Quiz history (last 10 attempts stored as JSON)
    quiz_history = Column(String(500), nullable=False, default="[]")  # JSON array of quiz results
    total_attempts = Column(Integer, nullable=False, default=0)
    correct_attempts = Column(Integer, nullable=False, default=0)

    # Timestamps
    first_attempt_at = Column(DateTime, nullable=True)
    last_attempt_at = Column(DateTime, nullable=True)
    last_correct_at = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    def __str__(self):
        return f"WeakListWord(word='{self.word.foreign}', accuracy={self.accuracy_percentage:.1f}%)"

    @property
    def quiz_results(self) -> list:
        """Get quiz history as list of dictionaries"""
        try:
            return json.loads(self.quiz_history) if self.quiz_history else []
        except json.JSONDecodeError:
            return []

    @property
    def accuracy_percentage(self) -> float:
        """Calculate accuracy percentage"""
        if self.total_attempts == 0:
            return 0.0
        return (self.correct_attempts / self.total_attempts) * 100.0

    @property
    def recent_accuracy(self) -> float:
        """Calculate accuracy for last 5 attempts"""
        recent_results = self.quiz_results[-5:] if len(self.quiz_results) >= 5 else self.quiz_results
        if not recent_results:
            return 0.0

        correct_recent = sum(1 for result in recent_results if result.get('is_correct', False))
        return (correct_recent / len(recent_results)) * 100.0

    @property
    def needs_review(self) -> bool:
        """Check if word needs review based on performance"""
        # Needs review if:
        # 1. Overall accuracy < 60%
        # 2. Recent accuracy < 50%
        # 3. Last 2 attempts were wrong
        # 4. Haven't been correct in last 5 attempts

        if self.accuracy_percentage < 60.0:
            return True

        if self.recent_accuracy < 50.0:
            return True

        recent_results = self.quiz_results[-2:]
        if len(recent_results) >= 2 and not any(r.get('is_correct', False) for r in recent_results):
            return True

        last_5_results = self.quiz_results[-5:]
        if len(last_5_results) >= 5 and not any(r.get('is_correct', False) for r in last_5_results):
            return True

        return False

    @property
    def is_mastered(self) -> bool:
        """Check if word is well learned (accuracy >= 80% with at least 5 attempts)"""
        return self.total_attempts >= 5 and self.accuracy_percentage >= 80.0

    @property
    def performance_level(self) -> str:
        """Get performance level: excellent, good, weak, critical"""
        accuracy = self.accuracy_percentage

        if accuracy >= 90.0:
            return "excellent"
        elif accuracy >= 80.0:
            return "good"
        elif accuracy >= 60.0:
            return "weak"
        else:
            return "critical"

    def record_quiz_attempt(self, is_correct: bool, quiz_type: str = "multiple_choice", response_time_ms: int = None):
        """Record a new quiz attempt"""
        now = datetime.utcnow()

        # Update counters
        self.total_attempts += 1
        if is_correct:
            self.correct_attempts += 1
            self.last_correct_at = now

        # Update timestamps
        if self.first_attempt_at is None:
            self.first_attempt_at = now
        self.last_attempt_at = now

        # Add to quiz history (keep only last 10)
        current_history = self.quiz_results

        new_attempt = {
            "is_correct": is_correct,
            "quiz_type": quiz_type,
            "timestamp": now.isoformat(),
            "response_time_ms": response_time_ms
        }

        current_history.append(new_attempt)

        # Keep only last 10 attempts
        if len(current_history) > 10:
            current_history = current_history[-10:]

        self.quiz_history = json.dumps(current_history)

    def get_mistake_pattern(self) -> dict:
        """Analyze mistake patterns"""
        results = self.quiz_results
        if not results:
            return {"total_mistakes": 0, "recent_mistakes": 0, "mistake_streak": 0}

        total_mistakes = sum(1 for r in results if not r.get('is_correct', False))
        recent_mistakes = sum(1 for r in results[-5:] if not r.get('is_correct', False))

        # Calculate current mistake streak (consecutive wrong answers from the end)
        mistake_streak = 0
        for result in reversed(results):
            if not result.get('is_correct', False):
                mistake_streak += 1
            else:
                break

        return {
            "total_mistakes": total_mistakes,
            "recent_mistakes": recent_mistakes,
            "mistake_streak": mistake_streak,
            "needs_urgent_review": mistake_streak >= 3 or recent_mistakes >= 4
        }
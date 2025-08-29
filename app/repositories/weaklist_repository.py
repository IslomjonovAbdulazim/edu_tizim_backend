from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc
from datetime import datetime, timedelta
from app.models.weaklist import WeakList, WeakListWord
from app.models.word import Word
from app.models.user import User
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.course import Course
from app.repositories.base_repository import BaseRepository


class WeakListRepository(BaseRepository[WeakList]):
    def __init__(self):
        super().__init__(WeakList)

    def get_or_create_user_weaklist(self, db: Session, user_id: int) -> WeakList:
        """Get or create weak list for a user"""
        weak_list = db.query(WeakList).filter(WeakList.user_id == user_id).first()

        if not weak_list:
            weak_list_data = {
                "user_id": user_id,
                "is_active": True
            }
            weak_list = self.create(db, weak_list_data)

        return weak_list

    def add_word_to_weaklist(self, db: Session, user_id: int, word_id: int) -> WeakListWord:
        """Add a word to user's weak list"""
        weak_list = self.get_or_create_user_weaklist(db, user_id)

        # Check if word already exists in weak list
        existing = db.query(WeakListWord).filter(
            and_(
                WeakListWord.weak_list_id == weak_list.id,
                WeakListWord.word_id == word_id
            )
        ).first()

        if existing:
            return existing

        # Create new weak list word
        weak_list_word_data = {
            "weak_list_id": weak_list.id,
            "word_id": word_id,
            "quiz_history": "[]",
            "total_attempts": 0,
            "correct_attempts": 0,
            "is_active": True
        }

        weak_list_word = WeakListWord(**weak_list_word_data)
        db.add(weak_list_word)
        db.commit()
        db.refresh(weak_list_word)

        return weak_list_word

    def record_quiz_attempt(
            self,
            db: Session,
            user_id: int,
            word_id: int,
            is_correct: bool,
            quiz_type: str = "multiple_choice",
            response_time_ms: Optional[int] = None
    ) -> WeakListWord:
        """Record a quiz attempt for a word"""

        # Get or create weak list word
        weak_list_word = self.add_word_to_weaklist(db, user_id, word_id)

        # Record the attempt
        weak_list_word.record_quiz_attempt(is_correct, quiz_type, response_time_ms)

        db.commit()
        db.refresh(weak_list_word)

        return weak_list_word

    def get_user_weaklist(self, db: Session, user_id: int) -> Optional[WeakList]:
        """Get user's weak list with all words"""
        return db.query(WeakList).filter(WeakList.user_id == user_id).options(
            joinedload(WeakList.words).joinedload(WeakListWord.word).joinedload(Word.lesson)
        ).first()

    def get_words_needing_review(self, db: Session, user_id: int, limit: int = 20) -> List[WeakListWord]:
        """Get words that need review (poor performance)"""
        weak_list = self.get_user_weaklist(db, user_id)
        if not weak_list:
            return []

        # Filter words that need review and sort by priority
        review_words = [w for w in weak_list.words if w.needs_review and w.is_active]

        # Sort by priority: worst accuracy first, then by recent mistakes
        review_words.sort(key=lambda w: (
            w.accuracy_percentage,  # Lower accuracy = higher priority
            -w.recent_accuracy,  # Lower recent accuracy = higher priority
            -w.get_mistake_pattern()["mistake_streak"]  # Longer mistake streak = higher priority
        ))

        return review_words[:limit]

    def get_weakest_words(self, db: Session, user_id: int, limit: int = 10) -> List[WeakListWord]:
        """Get user's weakest words (lowest accuracy)"""
        weak_list = self.get_user_weaklist(db, user_id)
        if not weak_list:
            return []

        # Filter words with at least 3 attempts and sort by accuracy
        weak_words = [w for w in weak_list.words if w.total_attempts >= 3 and w.is_active]
        weak_words.sort(key=lambda w: w.accuracy_percentage)

        return weak_words[:limit]

    def get_strongest_words(self, db: Session, user_id: int, limit: int = 10) -> List[WeakListWord]:
        """Get user's strongest words (highest accuracy)"""
        weak_list = self.get_user_weaklist(db, user_id)
        if not weak_list:
            return []

        # Filter words with good performance
        strong_words = [w for w in weak_list.words if
                        w.total_attempts >= 5 and w.accuracy_percentage >= 80.0 and w.is_active]
        strong_words.sort(key=lambda w: -w.accuracy_percentage)  # Descending order

        return strong_words[:limit]

    def get_mastered_words(self, db: Session, user_id: int) -> List[WeakListWord]:
        """Get words user has mastered"""
        weak_list = self.get_user_weaklist(db, user_id)
        if not weak_list:
            return []

        return [w for w in weak_list.words if w.is_mastered and w.is_active]

    def remove_mastered_words(self, db: Session, user_id: int) -> int:
        """Remove mastered words from weak list"""
        weak_list = self.get_user_weaklist(db, user_id)
        if not weak_list:
            return 0

        mastered_count = 0
        for word in weak_list.words:
            if word.is_mastered:
                word.is_active = False
                mastered_count += 1

        db.commit()
        return mastered_count

    def get_quiz_statistics(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get comprehensive quiz statistics for user"""
        weak_list = self.get_user_weaklist(db, user_id)
        if not weak_list:
            return self._empty_stats()

        active_words = [w for w in weak_list.words if w.is_active]

        if not active_words:
            return self._empty_stats()

        total_words = len(active_words)
        total_attempts = sum(w.total_attempts for w in active_words)
        total_correct = sum(w.correct_attempts for w in active_words)

        # Performance categories
        excellent = len([w for w in active_words if w.performance_level == "excellent"])
        good = len([w for w in active_words if w.performance_level == "good"])
        weak = len([w for w in active_words if w.performance_level == "weak"])
        critical = len([w for w in active_words if w.performance_level == "critical"])

        # Recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_active_words = [w for w in active_words if w.last_attempt_at and w.last_attempt_at >= week_ago]

        return {
            "total_words": total_words,
            "total_attempts": total_attempts,
            "overall_accuracy": (total_correct / total_attempts * 100) if total_attempts > 0 else 0,
            "words_needing_review": len([w for w in active_words if w.needs_review]),
            "mastered_words": len([w for w in active_words if w.is_mastered]),
            "performance_breakdown": {
                "excellent": excellent,
                "good": good,
                "weak": weak,
                "critical": critical
            },
            "recent_activity": {
                "words_practiced_week": len(recent_active_words),
                "attempts_this_week": sum(len([r for r in w.quiz_results if datetime.fromisoformat(
                    r['timestamp'].replace('Z', '+00:00')) >= week_ago]) for w in active_words)
            }
        }

    def get_word_performance(self, db: Session, user_id: int, word_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed performance for a specific word"""
        weak_list = self.get_user_weaklist(db, user_id)
        if not weak_list:
            return None

        weak_list_word = next((w for w in weak_list.words if w.word_id == word_id), None)
        if not weak_list_word:
            return None

        return {
            "word_id": word_id,
            "word_foreign": weak_list_word.word.foreign,
            "word_local": weak_list_word.word.local,
            "total_attempts": weak_list_word.total_attempts,
            "correct_attempts": weak_list_word.correct_attempts,
            "accuracy_percentage": weak_list_word.accuracy_percentage,
            "recent_accuracy": weak_list_word.recent_accuracy,
            "performance_level": weak_list_word.performance_level,
            "needs_review": weak_list_word.needs_review,
            "is_mastered": weak_list_word.is_mastered,
            "quiz_history": weak_list_word.quiz_results,
            "mistake_pattern": weak_list_word.get_mistake_pattern(),
            "first_attempt": weak_list_word.first_attempt_at.isoformat() if weak_list_word.first_attempt_at else None,
            "last_attempt": weak_list_word.last_attempt_at.isoformat() if weak_list_word.last_attempt_at else None,
            "last_correct": weak_list_word.last_correct_at.isoformat() if weak_list_word.last_correct_at else None
        }

    def get_learning_suggestions(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get personalized learning suggestions"""
        stats = self.get_quiz_statistics(db, user_id)
        review_words = self.get_words_needing_review(db, user_id, limit=5)

        suggestions = []

        if stats["words_needing_review"] > 0:
            suggestions.append({
                "type": "review_weak_words",
                "priority": "high",
                "message": f"You have {stats['words_needing_review']} words that need review",
                "action": "Practice your weakest words to improve accuracy"
            })

        if stats["performance_breakdown"]["critical"] > 0:
            suggestions.append({
                "type": "critical_words",
                "priority": "urgent",
                "message": f"{stats['performance_breakdown']['critical']} words need immediate attention",
                "action": "Focus on words with very low accuracy first"
            })

        if stats["recent_activity"]["words_practiced_week"] < 5:
            suggestions.append({
                "type": "increase_practice",
                "priority": "medium",
                "message": "Try to practice more consistently",
                "action": "Aim to practice at least 10 words daily"
            })

        return {
            "suggestions": suggestions,
            "focus_words": [
                {
                    "word_id": w.word_id,
                    "word": f"{w.word.foreign} - {w.word.local}",
                    "accuracy": w.accuracy_percentage,
                    "attempts": w.total_attempts
                }
                for w in review_words[:3]
            ]
        }

    def bulk_record_quiz_session(
            self,
            db: Session,
            user_id: int,
            quiz_attempts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Record multiple quiz attempts in one session"""
        results = {
            "total_attempts": len(quiz_attempts),
            "correct_count": 0,
            "words_updated": [],
            "new_review_words": []
        }

        for attempt in quiz_attempts:
            word_id = attempt["word_id"]
            is_correct = attempt["is_correct"]
            quiz_type = attempt.get("quiz_type", "multiple_choice")
            response_time = attempt.get("response_time_ms")

            weak_list_word = self.record_quiz_attempt(
                db, user_id, word_id, is_correct, quiz_type, response_time
            )

            if is_correct:
                results["correct_count"] += 1

            results["words_updated"].append({
                "word_id": word_id,
                "accuracy": weak_list_word.accuracy_percentage,
                "needs_review": weak_list_word.needs_review
            })

            if weak_list_word.needs_review:
                results["new_review_words"].append(word_id)

        results["accuracy"] = (results["correct_count"] / results["total_attempts"] * 100) if results[
                                                                                                  "total_attempts"] > 0 else 0

        return results

    def _empty_stats(self) -> Dict[str, Any]:
        """Return empty statistics structure"""
        return {
            "total_words": 0,
            "total_attempts": 0,
            "overall_accuracy": 0,
            "words_needing_review": 0,
            "mastered_words": 0,
            "performance_breakdown": {
                "excellent": 0,
                "good": 0,
                "weak": 0,
                "critical": 0
            },
            "recent_activity": {
                "words_practiced_week": 0,
                "attempts_this_week": 0
            }
        }


class WeakListWordRepository(BaseRepository[WeakListWord]):
    def __init__(self):
        super().__init__(WeakListWord)

    def get_word_quiz_history(self, db: Session, user_id: int, word_id: int) -> Optional[WeakListWord]:
        """Get quiz history for a specific word"""
        return db.query(WeakListWord).join(WeakList).filter(
            and_(
                WeakList.user_id == user_id,
                WeakListWord.word_id == word_id,
                WeakListWord.is_active == True
            )
        ).options(joinedload(WeakListWord.word)).first()

    def reset_word_progress(self, db: Session, user_id: int, word_id: int) -> bool:
        """Reset progress for a specific word"""
        weak_list_word = self.get_word_quiz_history(db, user_id, word_id)
        if not weak_list_word:
            return False

        weak_list_word.quiz_history = "[]"
        weak_list_word.total_attempts = 0
        weak_list_word.correct_attempts = 0
        weak_list_word.first_attempt_at = None
        weak_list_word.last_attempt_at = None
        weak_list_word.last_correct_at = None

        db.commit()
        return True
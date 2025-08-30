from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func, asc
from datetime import datetime, timedelta
from app.models.learning import Progress, QuizSession, WeakWord
from app.repositories.base import BaseRepository


class ProgressRepository(BaseRepository):
    """Progress repository for lesson completion tracking"""

    def __init__(self, db: Session):
        super().__init__(db, Progress)

    def get_user_progress(self, user_id: int) -> List[Progress]:
        """Get all progress records for user"""
        return self.db.query(Progress).options(
            joinedload(Progress.lesson),
            joinedload(Progress.user)
        ).filter(
            and_(
                Progress.user_id == user_id,
                Progress.is_active == True
            )
        ).order_by(desc(Progress.updated_at)).all()

    def get_by_user_lesson(self, user_id: int, lesson_id: int) -> Optional[Progress]:
        """Get progress for specific user and lesson"""
        return self.db.query(Progress).filter(
            and_(
                Progress.user_id == user_id,
                Progress.lesson_id == lesson_id,
                Progress.is_active == True
            )
        ).first()

    def get_lesson_progress(self, lesson_id: int) -> List[Progress]:
        """Get all progress records for a lesson"""
        return self.db.query(Progress).filter(
            and_(
                Progress.lesson_id == lesson_id,
                Progress.is_active == True
            )
        ).all()

    def get_completed_lessons(self, user_id: int) -> List[Progress]:
        """Get completed lessons for user"""
        return self.db.query(Progress).filter(
            and_(
                Progress.user_id == user_id,
                Progress.is_completed == True,
                Progress.is_active == True
            )
        ).order_by(desc(Progress.updated_at)).all()

    def get_perfect_lessons_count(self, user_id: int) -> int:
        """Get count of lessons completed with 100% accuracy"""
        return self.db.query(Progress).filter(
            and_(
                Progress.user_id == user_id,
                Progress.completion_percentage >= 100.0,
                Progress.is_active == True
            )
        ).count()

    def update_progress(self, user_id: int, lesson_id: int, completion_percentage: float,
                        points: int = None, correct_answers: int = None, total_attempts: int = None) -> Progress:
        """Update or create progress record"""
        progress = self.get_by_user_lesson(user_id, lesson_id)

        if progress:
            # Update existing progress
            progress.completion_percentage = completion_percentage
            progress.is_completed = completion_percentage >= 100.0
            progress.last_attempt_at = datetime.utcnow()

            if points is not None:
                progress.points = max(progress.points, points)  # Keep highest score
            if correct_answers is not None and total_attempts is not None:
                progress.correct_answers += correct_answers
                progress.total_attempts += total_attempts

            self.db.commit()
            self.db.refresh(progress)
        else:
            # Create new progress record
            progress_data = {
                "user_id": user_id,
                "lesson_id": lesson_id,
                "completion_percentage": completion_percentage,
                "points": points or int(completion_percentage),
                "is_completed": completion_percentage >= 100.0,
                "correct_answers": correct_answers or 0,
                "total_attempts": total_attempts or 0,
                "last_attempt_at": datetime.utcnow()
            }
            progress = self.create(progress_data)

        return progress

    def get_user_total_points(self, user_id: int) -> int:
        """Get total points earned by user"""
        result = self.db.query(func.sum(Progress.points)).filter(
            and_(
                Progress.user_id == user_id,
                Progress.is_active == True
            )
        ).scalar()
        return result or 0

    def get_center_progress_stats(self, learning_center_id: int) -> Dict[str, Any]:
        """Get progress statistics for learning center"""
        # This requires joining with lessons -> modules -> courses
        from app.models.content import Lesson, Module, Course

        total_progress = self.db.query(Progress).join(Lesson).join(Module).join(Course).filter(
            and_(
                Course.learning_center_id == learning_center_id,
                Progress.is_active == True
            )
        ).count()

        completed_lessons = self.db.query(Progress).join(Lesson).join(Module).join(Course).filter(
            and_(
                Course.learning_center_id == learning_center_id,
                Progress.is_completed == True,
                Progress.is_active == True
            )
        ).count()

        average_completion = self.db.query(func.avg(Progress.completion_percentage)).join(Lesson).join(Module).join(
            Course).filter(
            and_(
                Course.learning_center_id == learning_center_id,
                Progress.is_active == True
            )
        ).scalar() or 0

        return {
            "total_progress_records": total_progress,
            "completed_lessons": completed_lessons,
            "average_completion_rate": float(average_completion),
            "completion_rate": (completed_lessons / total_progress * 100) if total_progress > 0 else 0
        }

    def get_recent_activity(self, user_id: int, days: int = 7) -> List[Progress]:
        """Get user's recent learning activity"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        return self.db.query(Progress).filter(
            and_(
                Progress.user_id == user_id,
                Progress.last_attempt_at >= cutoff_date,
                Progress.is_active == True
            )
        ).order_by(desc(Progress.last_attempt_at)).all()

    def get_struggling_lessons(self, user_id: int, min_attempts: int = 3) -> List[Progress]:
        """Get lessons user is struggling with (many attempts, low completion)"""
        return self.db.query(Progress).filter(
            and_(
                Progress.user_id == user_id,
                Progress.total_attempts >= min_attempts,
                Progress.completion_percentage < 80.0,
                Progress.is_active == True
            )
        ).order_by(desc(Progress.total_attempts)).all()

    def reset_progress(self, user_id: int, lesson_id: int) -> Optional[Progress]:
        """Reset progress for specific lesson (admin function)"""
        progress = self.get_by_user_lesson(user_id, lesson_id)
        if progress:
            return self.update(progress.id, {
                "completion_percentage": 0.0,
                "points": 0,
                "is_completed": False,
                "total_attempts": 0,
                "correct_answers": 0,
                "last_attempt_at": None
            })
        return None


class QuizSessionRepository(BaseRepository):
    """Quiz session repository for tracking quiz attempts"""

    def __init__(self, db: Session):
        super().__init__(db, QuizSession)

    def get_active_session(self, user_id: int, lesson_id: int) -> Optional[QuizSession]:
        """Get active (incomplete) quiz session"""
        return self.db.query(QuizSession).filter(
            and_(
                QuizSession.user_id == user_id,
                QuizSession.lesson_id == lesson_id,
                QuizSession.is_completed == False,
                QuizSession.is_active == True
            )
        ).first()

    def create_session(self, user_id: int, lesson_id: int) -> QuizSession:
        """Create new quiz session"""
        session_data = {
            "user_id": user_id,
            "lesson_id": lesson_id,
            "started_at": datetime.utcnow(),
            "is_completed": False
        }
        return self.create(session_data)

    def complete_session(self, session_id: int, quiz_results: Dict[int, bool]) -> Optional[QuizSession]:
        """Complete quiz session with results"""
        session = self.get(session_id)
        if not session:
            return None

        total_questions = len(quiz_results)
        correct_answers = sum(1 for result in quiz_results.values() if result)
        completion_percentage = (correct_answers / total_questions * 100) if total_questions > 0 else 0

        update_data = {
            "quiz_results": quiz_results,
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "completion_percentage": completion_percentage,
            "completed_at": datetime.utcnow(),
            "is_completed": True
        }

        return self.update(session_id, update_data)

    def get_user_sessions(self, user_id: int) -> List[QuizSession]:
        """Get all quiz sessions for user"""
        return self.db.query(QuizSession).filter(
            and_(
                QuizSession.user_id == user_id,
                QuizSession.is_active == True
            )
        ).order_by(desc(QuizSession.started_at)).all()

    def get_recent_sessions(self, user_id: int, limit: int = 20) -> List[QuizSession]:
        """Get recent quiz sessions for user"""
        return self.db.query(QuizSession).filter(
            and_(
                QuizSession.user_id == user_id,
                QuizSession.is_active == True
            )
        ).order_by(desc(QuizSession.started_at)).limit(limit).all()

    def get_lesson_sessions(self, lesson_id: int) -> List[QuizSession]:
        """Get all quiz sessions for a lesson"""
        return self.db.query(QuizSession).filter(
            and_(
                QuizSession.lesson_id == lesson_id,
                QuizSession.is_active == True
            )
        ).order_by(desc(QuizSession.started_at)).all()

    def get_completed_sessions(self, user_id: int) -> List[QuizSession]:
        """Get completed quiz sessions for user"""
        return self.db.query(QuizSession).filter(
            and_(
                QuizSession.user_id == user_id,
                QuizSession.is_completed == True,
                QuizSession.is_active == True
            )
        ).order_by(desc(QuizSession.completed_at)).all()

    def get_session_stats(self, user_id: int) -> Dict[str, Any]:
        """Get quiz statistics for user"""
        completed_sessions = self.get_completed_sessions(user_id)

        if not completed_sessions:
            return {
                "total_sessions": 0,
                "average_accuracy": 0.0,
                "total_questions_answered": 0,
                "total_correct_answers": 0,
                "best_accuracy": 0.0,
                "recent_accuracy": 0.0
            }

        total_questions = sum(s.total_questions for s in completed_sessions)
        total_correct = sum(s.correct_answers for s in completed_sessions)
        best_accuracy = max(s.accuracy for s in completed_sessions)

        # Recent accuracy (last 5 sessions)
        recent_sessions = completed_sessions[:5]
        recent_questions = sum(s.total_questions for s in recent_sessions)
        recent_correct = sum(s.correct_answers for s in recent_sessions)
        recent_accuracy = (recent_correct / recent_questions * 100) if recent_questions > 0 else 0

        return {
            "total_sessions": len(completed_sessions),
            "average_accuracy": (total_correct / total_questions * 100) if total_questions > 0 else 0,
            "total_questions_answered": total_questions,
            "total_correct_answers": total_correct,
            "best_accuracy": best_accuracy,
            "recent_accuracy": recent_accuracy
        }

    def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Clean up old incomplete sessions"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        old_sessions = self.db.query(QuizSession).filter(
            and_(
                QuizSession.is_completed == False,
                QuizSession.started_at < cutoff_date
            )
        ).all()

        for session in old_sessions:
            self.soft_delete(session.id)

        return len(old_sessions)


class WeakWordRepository(BaseRepository):
    """Weak word repository for vocabulary difficulty tracking"""

    def __init__(self, db: Session):
        super().__init__(db, WeakWord)

    def get_user_weak_words(self, user_id: int) -> List[WeakWord]:
        """Get all weak words for user with word details"""
        return self.db.query(WeakWord).options(
            joinedload(WeakWord.word)
        ).filter(
            and_(
                WeakWord.user_id == user_id,
                WeakWord.is_active == True
            )
        ).order_by(desc(WeakWord.last_attempt_at)).all()

    def get_by_user_word(self, user_id: int, word_id: int) -> Optional[WeakWord]:
        """Get weak word record for specific user and word"""
        return self.db.query(WeakWord).filter(
            and_(
                WeakWord.user_id == user_id,
                WeakWord.word_id == word_id,
                WeakWord.is_active == True
            )
        ).first()

    def add_attempt(self, user_id: int, word_id: int, is_correct: bool) -> WeakWord:
        """Add attempt for word and update strength"""
        weak_word = self.get_by_user_word(user_id, word_id)

        if weak_word:
            # Update existing record
            weak_word.add_attempt(is_correct)
            self.db.commit()
            self.db.refresh(weak_word)
        else:
            # Create new record
            weak_word_data = {
                "user_id": user_id,
                "word_id": word_id,
                "last_7_results": "1" if is_correct else "0",
                "total_attempts": 1,
                "correct_attempts": 1 if is_correct else 0,
                "strength": "medium" if is_correct else "weak",
                "last_attempt_at": datetime.utcnow()
            }
            weak_word = self.create(weak_word_data)

        return weak_word

    def process_quiz_results(self, user_id: int, quiz_results: Dict[int, bool]) -> List[WeakWord]:
        """Process quiz results and update weak words"""
        updated_words = []

        for word_id, is_correct in quiz_results.items():
            weak_word = self.add_attempt(user_id, word_id, is_correct)
            updated_words.append(weak_word)

        return updated_words

    def get_weak_words_by_strength(self, user_id: int, strength: str) -> List[WeakWord]:
        """Get weak words by strength level"""
        return self.db.query(WeakWord).options(
            joinedload(WeakWord.word)
        ).filter(
            and_(
                WeakWord.user_id == user_id,
                WeakWord.strength == strength,
                WeakWord.is_active == True
            )
        ).order_by(desc(WeakWord.last_attempt_at)).all()

    def get_practice_words(self, user_id: int, limit: int = 20) -> List[WeakWord]:
        """Get words for practice (prioritize weak words)"""
        return self.db.query(WeakWord).options(
            joinedload(WeakWord.word)
        ).filter(
            and_(
                WeakWord.user_id == user_id,
                WeakWord.strength.in_(["weak", "medium"]),
                WeakWord.is_active == True
            )
        ).order_by(
            # Prioritize weak words first, then by recent attempts
            asc(func.case([(WeakWord.strength == "weak", 1)], else_=2)),
            desc(WeakWord.last_attempt_at)
        ).limit(limit).all()

    def get_mastered_words_count(self, user_id: int) -> int:
        """Get count of mastered (strong) words"""
        return self.db.query(WeakWord).filter(
            and_(
                WeakWord.user_id == user_id,
                WeakWord.strength == "strong",
                WeakWord.is_active == True
            )
        ).count()

    def get_weak_words_count(self, user_id: int) -> int:
        """Get count of weak words"""
        return self.db.query(WeakWord).filter(
            and_(
                WeakWord.user_id == user_id,
                WeakWord.strength == "weak",
                WeakWord.is_active == True
            )
        ).count()

    def get_words_needing_review(self, user_id: int, days_since_attempt: int = 7) -> List[WeakWord]:
        """Get words that need review (not attempted recently)"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_since_attempt)

        return self.db.query(WeakWord).options(
            joinedload(WeakWord.word)
        ).filter(
            and_(
                WeakWord.user_id == user_id,
                WeakWord.strength.in_(["weak", "medium"]),
                WeakWord.last_attempt_at < cutoff_date,
                WeakWord.is_active == True
            )
        ).order_by(asc(WeakWord.last_attempt_at)).all()

    def get_improvement_candidates(self, user_id: int) -> List[WeakWord]:
        """Get words that are improving (medium strength with good recent accuracy)"""
        return self.db.query(WeakWord).options(
            joinedload(WeakWord.word)
        ).filter(
            and_(
                WeakWord.user_id == user_id,
                WeakWord.strength == "medium",
                WeakWord.is_active == True
            )
        ).all()

    def get_vocabulary_stats(self, user_id: int) -> Dict[str, Any]:
        """Get vocabulary statistics for user"""
        weak_words = self.get_user_weak_words(user_id)

        if not weak_words:
            return {
                "total_words_encountered": 0,
                "weak_words": 0,
                "medium_words": 0,
                "strong_words": 0,
                "overall_accuracy": 0.0,
                "total_attempts": 0,
                "vocabulary_strength": 0.0
            }

        strength_counts = {"weak": 0, "medium": 0, "strong": 0}
        total_attempts = sum(w.total_attempts for w in weak_words)
        total_correct = sum(w.correct_attempts for w in weak_words)

        for word in weak_words:
            strength_counts[word.strength] += 1

        overall_accuracy = (total_correct / total_attempts * 100) if total_attempts > 0 else 0
        vocabulary_strength = (strength_counts["strong"] / len(weak_words) * 100) if weak_words else 0

        return {
            "total_words_encountered": len(weak_words),
            "weak_words": strength_counts["weak"],
            "medium_words": strength_counts["medium"],
            "strong_words": strength_counts["strong"],
            "overall_accuracy": overall_accuracy,
            "total_attempts": total_attempts,
            "vocabulary_strength": vocabulary_strength
        }

    def reset_word_progress(self, user_id: int, word_id: int) -> Optional[WeakWord]:
        """Reset progress for specific word (admin function)"""
        weak_word = self.get_by_user_word(user_id, word_id)
        if weak_word:
            return self.update(weak_word.id, {
                "last_7_results": "",
                "total_attempts": 0,
                "correct_attempts": 0,
                "strength": "weak",
                "last_attempt_at": None
            })
        return None
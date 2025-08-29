from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime
from app.models import Progress, QuizSession, WeakWord, Word, Lesson
from app.repositories.base import BaseRepository


class ProgressRepository(BaseRepository[Progress]):
    def __init__(self, db: Session):
        super().__init__(Progress, db)

    def get_by_user_lesson(self, user_id: int, lesson_id: int) -> Optional[Progress]:
        """Get progress for specific user and lesson"""
        return self.db.query(Progress).filter(
            and_(
                Progress.user_id == user_id,
                Progress.lesson_id == lesson_id
            )
        ).first()

    def get_user_progress(self, user_id: int) -> List[Progress]:
        """Get all progress records for user"""
        return self.db.query(Progress).filter(Progress.user_id == user_id).all()

    def get_lesson_progress(self, lesson_id: int) -> List[Progress]:
        """Get all progress records for lesson"""
        return self.db.query(Progress).filter(Progress.lesson_id == lesson_id).all()

    def get_completed_lessons(self, user_id: int) -> List[Progress]:
        """Get completed lessons for user"""
        return self.db.query(Progress).filter(
            and_(
                Progress.user_id == user_id,
                Progress.is_completed == True
            )
        ).all()

    def update_progress(self, user_id: int, lesson_id: int, new_percentage: float) -> Optional[Progress]:
        """Update or create progress record"""
        progress = self.get_by_user_lesson(user_id, lesson_id)

        if not progress:
            # Create new progress record
            progress = Progress(
                user_id=user_id,
                lesson_id=lesson_id,
                completion_percentage=new_percentage,
                points=int(new_percentage),
                is_completed=new_percentage >= 100,
                total_attempts=1,
                correct_answers=int(new_percentage),
                last_attempt_at=datetime.utcnow()
            )
            self.db.add(progress)
        else:
            # Update existing progress if new percentage is higher
            if new_percentage > progress.completion_percentage:
                progress.completion_percentage = new_percentage
                progress.points = int(new_percentage)
                progress.is_completed = new_percentage >= 100
                progress.total_attempts += 1
                progress.correct_answers += int(new_percentage - progress.completion_percentage)
                progress.last_attempt_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(progress)
        return progress

    def get_user_total_points(self, user_id: int) -> int:
        """Get total points for user"""
        result = self.db.query(func.sum(Progress.points)).filter(
            Progress.user_id == user_id
        ).scalar()
        return result or 0

    def get_perfect_lessons_count(self, user_id: int) -> int:
        """Get count of lessons completed with 100% accuracy"""
        return self.db.query(Progress).filter(
            and_(
                Progress.user_id == user_id,
                Progress.completion_percentage >= 100
            )
        ).count()


class QuizSessionRepository(BaseRepository[QuizSession]):
    def __init__(self, db: Session):
        super().__init__(QuizSession, db)

    def get_user_sessions(self, user_id: int) -> List[QuizSession]:
        """Get all quiz sessions for user"""
        return self.db.query(QuizSession).filter(
            QuizSession.user_id == user_id
        ).order_by(QuizSession.started_at.desc()).all()

    def get_lesson_sessions(self, lesson_id: int) -> List[QuizSession]:
        """Get all quiz sessions for lesson"""
        return self.db.query(QuizSession).filter(
            QuizSession.lesson_id == lesson_id
        ).all()

    def get_user_lesson_sessions(self, user_id: int, lesson_id: int) -> List[QuizSession]:
        """Get quiz sessions for user and lesson"""
        return self.db.query(QuizSession).filter(
            and_(
                QuizSession.user_id == user_id,
                QuizSession.lesson_id == lesson_id
            )
        ).order_by(QuizSession.started_at.desc()).all()

    def create_session(self, user_id: int, lesson_id: Optional[int] = None) -> QuizSession:
        """Create new quiz session"""
        session = QuizSession(
            user_id=user_id,
            lesson_id=lesson_id,
            started_at=datetime.utcnow()
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def complete_session(self, session_id: int, quiz_results: Dict[int, bool]) -> Optional[QuizSession]:
        """Complete quiz session with results"""
        session = self.get(session_id)
        if not session:
            return None

        correct_answers = sum(1 for is_correct in quiz_results.values() if is_correct)
        total_questions = len(quiz_results)

        session.quiz_results = quiz_results
        session.total_questions = total_questions
        session.correct_answers = correct_answers
        session.completion_percentage = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        session.is_completed = True
        session.completed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(session)
        return session

    def get_active_session(self, user_id: int, lesson_id: Optional[int] = None) -> Optional[QuizSession]:
        """Get active (incomplete) session for user"""
        query = self.db.query(QuizSession).filter(
            and_(
                QuizSession.user_id == user_id,
                QuizSession.is_completed == False
            )
        )

        if lesson_id is not None:
            query = query.filter(QuizSession.lesson_id == lesson_id)

        return query.first()

    def get_recent_sessions(self, user_id: int, limit: int = 10) -> List[QuizSession]:
        """Get recent completed sessions for user"""
        return self.db.query(QuizSession).filter(
            and_(
                QuizSession.user_id == user_id,
                QuizSession.is_completed == True
            )
        ).order_by(QuizSession.completed_at.desc()).limit(limit).all()


class WeakWordRepository(BaseRepository[WeakWord]):
    def __init__(self, db: Session):
        super().__init__(WeakWord, db)

    def get_by_user_word(self, user_id: int, word_id: int) -> Optional[WeakWord]:
        """Get weak word record for user and word"""
        return self.db.query(WeakWord).filter(
            and_(
                WeakWord.user_id == user_id,
                WeakWord.word_id == word_id
            )
        ).first()

    def get_user_weak_words(self, user_id: int) -> List[WeakWord]:
        """Get all weak words for user"""
        return self.db.query(WeakWord).filter(WeakWord.user_id == user_id).all()

    def get_weak_words_by_strength(self, user_id: int, strength: str) -> List[WeakWord]:
        """Get weak words by strength level"""
        return self.db.query(WeakWord).filter(
            and_(
                WeakWord.user_id == user_id,
                WeakWord.strength == strength
            )
        ).all()

    def add_attempt(self, user_id: int, word_id: int, is_correct: bool) -> WeakWord:
        """Add attempt result for word"""
        weak_word = self.get_by_user_word(user_id, word_id)

        if not weak_word:
            # Create new weak word record
            weak_word = WeakWord(
                user_id=user_id,
                word_id=word_id,
                last_7_results="1" if is_correct else "0",
                total_attempts=1,
                correct_attempts=1 if is_correct else 0,
                strength="strong" if is_correct else "weak",
                last_attempt_at=datetime.utcnow()
            )
            self.db.add(weak_word)
        else:
            # Update existing record
            weak_word.add_attempt(is_correct)

        self.db.commit()
        self.db.refresh(weak_word)
        return weak_word

    def process_quiz_results(self, user_id: int, quiz_results: Dict[int, bool]) -> List[WeakWord]:
        """Process quiz results and update weak word records"""
        weak_words = []
        for word_id, is_correct in quiz_results.items():
            weak_word = self.add_attempt(user_id, word_id, is_correct)
            weak_words.append(weak_word)
        return weak_words

    def get_practice_words(self, user_id: int, limit: int = 20) -> List[WeakWord]:
        """Get weak words for practice (prioritize 'weak' strength)"""
        return self.db.query(WeakWord).filter(
            and_(
                WeakWord.user_id == user_id,
                WeakWord.strength.in_(["weak", "medium"])
            )
        ).order_by(WeakWord.strength.desc(), WeakWord.last_attempt_at.asc()).limit(limit).all()

    def get_words_needing_review(self, user_id: int) -> List[WeakWord]:
        """Get words that need review (weak strength or not practiced recently)"""
        return self.db.query(WeakWord).filter(
            and_(
                WeakWord.user_id == user_id,
                WeakWord.strength == "weak"
            )
        ).all()

    def get_mastered_words_count(self, user_id: int) -> int:
        """Get count of strong words for user"""
        return self.db.query(WeakWord).filter(
            and_(
                WeakWord.user_id == user_id,
                WeakWord.strength == "strong"
            )
        ).count()

    def get_weak_words_count(self, user_id: int) -> int:
        """Get count of weak words for user"""
        return self.db.query(WeakWord).filter(
            and_(
                WeakWord.user_id == user_id,
                WeakWord.strength == "weak"
            )
        ).count()

    def get_weaklist_completions_count(self, user_id: int) -> int:
        """Get count of words that moved from weak to strong"""
        # This is a simplified implementation - you might want to track this differently
        return self.get_mastered_words_count(user_id)
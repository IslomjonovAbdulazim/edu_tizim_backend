from __future__ import annotations
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.models.learning import Progress, QuizSession, WeakWord
from app.repositories.base import BaseRepository
from .base import BaseService


class LearningService(BaseService[Progress]):
    def __init__(self, db: Session):
        super().__init__(db)
        self.progress_repo = BaseRepository[Progress](db, Progress)
        self.quiz_repo = BaseRepository[QuizSession](db, QuizSession)
        self.weak_repo = BaseRepository[WeakWord](db, WeakWord)

    # progress
    def record_progress(self, data: Dict[str, Any]) -> Progress:
        return self.progress_repo.create(data)

    def get_user_progress(self, user_id: int, *, limit: int = 100) -> List[Progress]:
        return (
            self.db.query(Progress)
            .filter(and_(Progress.user_id == user_id, Progress.is_active.is_(True)))
            .order_by(desc(Progress.created_at))
            .limit(limit)
            .all()
        )

    # quizzes
    def start_quiz(self, data: Dict[str, Any]) -> QuizSession:
        return self.quiz_repo.create(data)

    def complete_quiz(self, quiz_id: int, updates: Dict[str, Any]) -> Optional[QuizSession]:
        return self.quiz_repo.update(quiz_id, updates)

    def get_user_quizzes(self, user_id: int, *, limit: int = 50) -> List[QuizSession]:
        return (
            self.db.query(QuizSession)
            .filter(and_(QuizSession.user_id == user_id, QuizSession.is_active.is_(True)))
            .order_by(desc(QuizSession.created_at))
            .limit(limit)
            .all()
        )

    # weak words
    def mark_weak_word(self, data: Dict[str, Any]) -> WeakWord:
        return self.weak_repo.create(data)

    def get_user_weak_words(self, user_id: int, *, limit: int = 100) -> List[WeakWord]:
        return (
            self.db.query(WeakWord)
            .filter(and_(WeakWord.user_id == user_id, WeakWord.is_active.is_(True)))
            .order_by(desc(WeakWord.created_at))
            .limit(limit)
            .all()
        )

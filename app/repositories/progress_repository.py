from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func
from datetime import datetime
from app.models.progress import Progress
from app.models.user import User
from app.models.lesson import Lesson
from app.repositories.base_repository import BaseRepository


class ProgressRepository(BaseRepository[Progress]):
    def __init__(self):
        super().__init__(Progress)

    def get_user_progress(self, db: Session, user_id: int, lesson_id: Optional[int] = None) -> List[Progress]:
        """Get user's progress records"""
        query = db.query(Progress).filter(Progress.user_id == user_id)

        if lesson_id:
            query = query.filter(Progress.lesson_id == lesson_id)

        return query.options(joinedload(Progress.lesson)).all()

    def get_lesson_progress(self, db: Session, lesson_id: int) -> List[Progress]:
        """Get all progress for a lesson"""
        return db.query(Progress).filter(Progress.lesson_id == lesson_id).options(
            joinedload(Progress.user)
        ).all()

    def update_progress(
            self,
            db: Session,
            user_id: int,
            lesson_id: int,
            correct_answers: int,
            total_questions: int,
            points: int,
            is_completed: bool = False
    ) -> Progress:
        """Update or create progress record"""
        progress = db.query(Progress).filter(
            and_(Progress.user_id == user_id, Progress.lesson_id == lesson_id)
        ).first()

        if not progress:
            progress = Progress(
                user_id=user_id,
                lesson_id=lesson_id,
                status="in_progress"
            )
            db.add(progress)

        # Update progress
        progress.attempts += 1
        progress.correct_answers = max(progress.correct_answers, correct_answers)
        progress.total_questions = max(progress.total_questions, total_questions)
        progress.points = max(progress.points, points)
        progress.last_attempt_at = datetime.utcnow()

        if is_completed:
            progress.is_completed = True
            progress.status = "completed"
        elif progress.status == "not_started":
            progress.status = "in_progress"

        db.commit()
        db.refresh(progress)
        return progress

    def get_user_statistics(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get user learning statistics"""
        progress_records = self.get_user_progress(db, user_id)

        completed = [p for p in progress_records if p.is_completed]
        in_progress = [p for p in progress_records if p.status == "in_progress" and not p.is_completed]

        total_points = sum(p.points for p in progress_records)
        avg_accuracy = 0.0

        if progress_records:
            accuracies = [p.accuracy for p in progress_records if p.total_questions > 0]
            avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0.0

        return {
            "total_lessons_attempted": len(progress_records),
            "lessons_completed": len(completed),
            "lessons_in_progress": len(in_progress),
            "total_points": total_points,
            "average_accuracy": round(avg_accuracy, 1),
            "completion_rate": round((len(completed) / len(progress_records)) * 100, 1) if progress_records else 0
        }

    def get_leaderboard_data(self, db: Session, learning_center_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Get leaderboard data for learning center"""
        return db.query(
            User.id,
            User.full_name,
            func.sum(Progress.points).label('total_points'),
            func.count(Progress.id).label('total_attempts'),
            func.sum(func.case([(Progress.is_completed == True, 1)], else_=0)).label('completed_lessons')
        ).join(Progress).filter(
            User.learning_center_id == learning_center_id
        ).group_by(
            User.id, User.full_name
        ).order_by(
            func.sum(Progress.points).desc()
        ).limit(limit).all()

    def get_course_progress(self, db: Session, user_id: int, course_id: int) -> Dict[str, Any]:
        """Get user's progress in a specific course"""
        # This would require joining through lesson -> module -> course
        # Simplified version for now
        progress_records = db.query(Progress).join(Lesson).join(
            Lesson.module
        ).filter(
            and_(
                Progress.user_id == user_id,
                # This would need proper course filtering
            )
        ).all()

        completed_lessons = len([p for p in progress_records if p.is_completed])
        total_points = sum(p.points for p in progress_records)

        return {
            "course_id": course_id,
            "lessons_completed": completed_lessons,
            "total_points": total_points,
            "progress_percentage": 0  # Would calculate based on total lessons in course
        }
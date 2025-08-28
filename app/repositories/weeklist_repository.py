from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc
from datetime import datetime, date, timedelta
from app.models.weeklist import WeekList, WeekListWord
from app.models.word import Word
from app.models.user import User
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.course import Course
from app.repositories.base_repository import BaseRepository


class WeekListRepository(BaseRepository[WeekList]):
    def __init__(self):
        super().__init__(WeekList)

    def get_user_weeklists(self, db: Session, user_id: int, active_only: bool = True) -> List[WeekList]:
        """Get all weekly lists for a user"""
        query = db.query(WeekList).filter(WeekList.user_id == user_id).options(
            joinedload(WeekList.user),
            joinedload(WeekList.words).joinedload(WeekListWord.word)
        )

        if active_only:
            query = query.filter(WeekList.is_active == True)

        return query.order_by(desc(WeekList.week_start_date)).all()

    def get_current_weeklist(self, db: Session, user_id: int) -> Optional[WeekList]:
        """Get current week's list for a user"""
        today = date.today()
        # Find Monday of current week
        monday = today - timedelta(days=today.weekday())

        return db.query(WeekList).filter(
            and_(
                WeekList.user_id == user_id,
                WeekList.week_start_date == monday,
                WeekList.is_active == True
            )
        ).options(
            joinedload(WeekList.words).joinedload(WeekListWord.word)
        ).first()

    def get_weeklist_by_date(self, db: Session, user_id: int, week_start_date: date) -> Optional[WeekList]:
        """Get weekly list for a specific week"""
        return db.query(WeekList).filter(
            and_(
                WeekList.user_id == user_id,
                WeekList.week_start_date == week_start_date
            )
        ).options(
            joinedload(WeekList.words).joinedload(WeekListWord.word)
        ).first()

    def create_weeklist(
            self,
            db: Session,
            user_id: int,
            week_start_date: date,
            word_ids: List[int],
            generation_context: Optional[str] = None
    ) -> WeekList:
        """Create a new weekly list with words"""
        week_end_date = week_start_date + timedelta(days=6)

        # Create weeklist
        weeklist_data = {
            "user_id": user_id,
            "week_start_date": week_start_date,
            "week_end_date": week_end_date,
            "generation_context": generation_context,
            "is_active": True,
            "is_completed": False
        }

        weeklist = self.create(db, weeklist_data)

        # Add words to the weeklist
        for priority, word_id in enumerate(word_ids):
            word_data = {
                "week_list_id": weeklist.id,
                "word_id": word_id,
                "priority_score": len(word_ids) - priority,  # Higher priority = higher score
                "difficulty_multiplier": 1,
                "practice_count": 0,
                "correct_count": 0,
                "is_mastered": False
            }

            weeklist_word = WeekListWord(**word_data)
            db.add(weeklist_word)

        db.commit()
        db.refresh(weeklist)
        return weeklist

    def get_weeklist_words(self, db: Session, weeklist_id: int) -> List[WeekListWord]:
        """Get all words in a weekly list with word details"""
        return db.query(WeekListWord).filter(
            WeekListWord.week_list_id == weeklist_id
        ).options(
            joinedload(WeekListWord.word).joinedload(Word.lesson).joinedload(Lesson.module).joinedload(Module.course)
        ).order_by(desc(WeekListWord.priority_score)).all()

    def record_word_practice(
            self,
            db: Session,
            weeklist_id: int,
            word_id: int,
            is_correct: bool
    ) -> WeekListWord:
        """Record a practice attempt for a word in weekly list"""
        weeklist_word = db.query(WeekListWord).filter(
            and_(
                WeekListWord.week_list_id == weeklist_id,
                WeekListWord.word_id == word_id
            )
        ).first()

        if weeklist_word:
            weeklist_word.record_practice(is_correct)
            db.commit()
            db.refresh(weeklist_word)

        return weeklist_word

    def bulk_record_practice(
            self,
            db: Session,
            weeklist_id: int,
            practice_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Record multiple practice attempts"""
        results = {
            "total_attempts": len(practice_data),
            "successful_updates": 0,
            "newly_mastered": [],
            "errors": []
        }

        for attempt in practice_data:
            try:
                word_id = attempt["word_id"]
                is_correct = attempt["is_correct"]

                weeklist_word = self.record_word_practice(db, weeklist_id, word_id, is_correct)

                if weeklist_word:
                    results["successful_updates"] += 1
                    # Check if newly mastered
                    if weeklist_word.is_mastered and weeklist_word.practice_count <= 5:
                        results["newly_mastered"].append(word_id)
                else:
                    results["errors"].append(f"Word {word_id} not found in weeklist")

            except Exception as e:
                results["errors"].append(f"Error processing word {attempt.get('word_id', 'unknown')}: {str(e)}")

        return results

    def get_mastered_words(self, db: Session, weeklist_id: int) -> List[WeekListWord]:
        """Get all mastered words from a weekly list"""
        return db.query(WeekListWord).filter(
            and_(
                WeekListWord.week_list_id == weeklist_id,
                WeekListWord.is_mastered == True
            )
        ).options(joinedload(WeekListWord.word)).all()

    def get_unmastered_words(self, db: Session, weeklist_id: int) -> List[WeekListWord]:
        """Get all unmastered words from a weekly list"""
        return db.query(WeekListWord).filter(
            and_(
                WeekListWord.week_list_id == weeklist_id,
                WeekListWord.is_mastered == False
            )
        ).options(joinedload(WeekListWord.word)).order_by(desc(WeekListWord.priority_score)).all()

    def mark_weeklist_completed(self, db: Session, weeklist_id: int) -> Optional[WeekList]:
        """Mark a weekly list as completed"""
        weeklist = self.get(db, weeklist_id)
        if weeklist:
            weeklist.is_completed = True
            db.commit()
            db.refresh(weeklist)
        return weeklist

    def get_weekly_statistics(self, db: Session, weeklist_id: int) -> Dict[str, Any]:
        """Get statistics for a weekly list"""
        weeklist = self.get(db, weeklist_id)
        if not weeklist:
            return {}

        words = self.get_weeklist_words(db, weeklist_id)

        total_words = len(words)
        mastered_words = len([w for w in words if w.is_mastered])
        total_attempts = sum(w.practice_count for w in words)
        total_correct = sum(w.correct_count for w in words)

        accuracy = (total_correct / total_attempts * 100) if total_attempts > 0 else 0.0
        completion_rate = (mastered_words / total_words * 100) if total_words > 0 else 0.0

        # Words by difficulty
        difficulty_stats = {}
        for word in words:
            difficulty = word.word.difficulty_level
            if difficulty not in difficulty_stats:
                difficulty_stats[difficulty] = {"total": 0, "mastered": 0}

            difficulty_stats[difficulty]["total"] += 1
            if word.is_mastered:
                difficulty_stats[difficulty]["mastered"] += 1

        return {
            "weeklist_id": weeklist_id,
            "week_start_date": weeklist.week_start_date,
            "week_end_date": weeklist.week_end_date,
            "total_words": total_words,
            "mastered_words": mastered_words,
            "unmastered_words": total_words - mastered_words,
            "total_attempts": total_attempts,
            "total_correct": total_correct,
            "accuracy_percentage": round(accuracy, 2),
            "completion_percentage": round(completion_rate, 2),
            "is_completed": weeklist.is_completed,
            "difficulty_breakdown": difficulty_stats
        }

    def get_user_weeklist_analytics(
            self,
            db: Session,
            user_id: int,
            weeks: int = 12
    ) -> Dict[str, Any]:
        """Get weekly list analytics for a user over specified weeks"""
        end_date = date.today()
        start_date = end_date - timedelta(weeks=weeks)

        weeklists = db.query(WeekList).filter(
            and_(
                WeekList.user_id == user_id,
                WeekList.week_start_date >= start_date,
                WeekList.week_start_date <= end_date
            )
        ).order_by(WeekList.week_start_date).all()

        total_weeklists = len(weeklists)
        completed_weeklists = len([w for w in weeklists if w.is_completed])

        # Get all words from these weeklists
        weeklist_ids = [w.id for w in weeklists]
        words = db.query(WeekListWord).filter(
            WeekListWord.week_list_id.in_(weeklist_ids)
        ).all() if weeklist_ids else []

        total_words = len(words)
        mastered_words = len([w for w in words if w.is_mastered])
        total_attempts = sum(w.practice_count for w in words)
        total_correct = sum(w.correct_count for w in words)

        # Calculate streak (consecutive weeks with completed lists)
        current_streak = 0
        for weeklist in reversed(weeklists):
            if weeklist.is_completed:
                current_streak += 1
            else:
                break

        # Weekly breakdown
        weekly_data = []
        for weeklist in weeklists:
            week_stats = self.get_weekly_statistics(db, weeklist.id)
            weekly_data.append(week_stats)

        return {
            "user_id": user_id,
            "analysis_period": {
                "start_date": start_date,
                "end_date": end_date,
                "weeks_analyzed": weeks
            },
            "summary": {
                "total_weeklists": total_weeklists,
                "completed_weeklists": completed_weeklists,
                "completion_rate": (completed_weeklists / total_weeklists * 100) if total_weeklists > 0 else 0.0,
                "total_words_practiced": total_words,
                "words_mastered": mastered_words,
                "mastery_rate": (mastered_words / total_words * 100) if total_words > 0 else 0.0,
                "total_practice_attempts": total_attempts,
                "overall_accuracy": (total_correct / total_attempts * 100) if total_attempts > 0 else 0.0,
                "current_streak": current_streak
            },
            "weekly_breakdown": weekly_data
        }

    def get_words_for_review(
            self,
            db: Session,
            user_id: int,
            weeks_back: int = 4,
            limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get words that need review from previous weeks"""
        end_date = date.today()
        start_date = end_date - timedelta(weeks=weeks_back)

        # Get words from previous weeklists that were not fully mastered
        query = db.query(WeekListWord).join(WeekList).filter(
            and_(
                WeekList.user_id == user_id,
                WeekList.week_start_date >= start_date,
                WeekList.week_start_date < end_date,
                or_(
                    WeekListWord.is_mastered == False,
                    WeekListWord.accuracy_percentage < 90.0  # Words with low accuracy need review
                )
            )
        ).options(
            joinedload(WeekListWord.word).joinedload(Word.lesson)
        ).order_by(WeekListWord.accuracy_percentage, desc(WeekListWord.practice_count)).limit(limit).all()

        review_words = []
        for weeklist_word in query:
            review_words.append({
                "word_id": weeklist_word.word.id,
                "foreign": weeklist_word.word.foreign,
                "local": weeklist_word.word.local,
                "accuracy": weeklist_word.accuracy_percentage,
                "practice_count": weeklist_word.practice_count,
                "last_week_practiced": weeklist_word.week_list.week_start_date,
                "priority_score": weeklist_word.priority_score,
                "needs_review": True
            })

        return review_words

    def cleanup_old_weeklists(self, db: Session, weeks_to_keep: int = 12) -> int:
        """Soft delete old weekly lists (mark as inactive)"""
        cutoff_date = date.today() - timedelta(weeks=weeks_to_keep)

        updated_count = db.query(WeekList).filter(
            and_(
                WeekList.week_start_date < cutoff_date,
                WeekList.is_active == True
            )
        ).update({"is_active": False})

        db.commit()
        return updated_count


class WeekListWordRepository(BaseRepository[WeekListWord]):
    def __init__(self):
        super().__init__(WeekListWord)

    def get_word_practice_history(self, db: Session, word_id: int, user_id: int) -> List[WeekListWord]:
        """Get practice history for a specific word across all weekly lists for a user"""
        return db.query(WeekListWord).join(WeekList).filter(
            and_(
                WeekListWord.word_id == word_id,
                WeekList.user_id == user_id
            )
        ).options(
            joinedload(WeekListWord.week_list),
            joinedload(WeekListWord.word)
        ).order_by(desc(WeekList.week_start_date)).all()

    def bulk_update_mastery_status(self, db: Session, weeklist_word_ids: List[int], is_mastered: bool) -> int:
        """Bulk update mastery status for multiple words"""
        updated_count = db.query(WeekListWord).filter(
            WeekListWord.id.in_(weeklist_word_ids)
        ).update({"is_mastered": is_mastered})

        db.commit()
        return updated_count

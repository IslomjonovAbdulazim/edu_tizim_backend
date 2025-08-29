from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc
from app.models.word import Word
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.course import Course
from app.repositories.base_repository import BaseRepository


class WordRepository(BaseRepository[Word]):
    def __init__(self):
        super().__init__(Word)

    def get_by_lesson(self, db: Session, lesson_id: int, active_only: bool = True) -> List[Word]:
        """Get words by lesson"""
        query = db.query(Word).filter(Word.lesson_id == lesson_id)

        if active_only:
            query = query.filter(Word.is_active == True)

        return query.order_by(Word.order_index, Word.created_at).all()

    def get_by_module(self, db: Session, module_id: int, active_only: bool = True) -> List[Word]:
        """Get all words in a module"""
        query = db.query(Word).join(Lesson).filter(Lesson.module_id == module_id)

        if active_only:
            query = query.filter(and_(Word.is_active == True, Lesson.is_active == True))

        return query.options(
            joinedload(Word.lesson).joinedload(Lesson.module)
        ).order_by(Lesson.order_index, Word.order_index).all()

    def get_by_course(self, db: Session, course_id: int, active_only: bool = True) -> List[Word]:
        """Get all words in a course"""
        query = db.query(Word).join(Lesson).join(Module).filter(Module.course_id == course_id)

        if active_only:
            query = query.filter(
                and_(
                    Word.is_active == True,
                    Lesson.is_active == True,
                    Module.is_active == True
                )
            )

        return query.options(
            joinedload(Word.lesson).joinedload(Lesson.module).joinedload(Module.course)
        ).order_by(Module.order_index, Lesson.order_index, Word.order_index).all()

    def get_by_learning_center(self, db: Session, learning_center_id: int, active_only: bool = True) -> List[Word]:
        """Get all words in a learning center"""
        query = db.query(Word).join(Lesson).join(Module).join(Course).filter(
            Course.learning_center_id == learning_center_id
        )

        if active_only:
            query = query.filter(
                and_(
                    Word.is_active == True,
                    Lesson.is_active == True,
                    Module.is_active == True,
                    Course.is_active == True
                )
            )

        return query.options(
            joinedload(Word.lesson).joinedload(Lesson.module).joinedload(Module.course)
        ).order_by(Course.order_index, Module.order_index, Lesson.order_index, Word.order_index).all()

    def search_words(
            self,
            db: Session,
            search_term: str,
            lesson_id: Optional[int] = None,
            module_id: Optional[int] = None,
            course_id: Optional[int] = None,
            learning_center_id: Optional[int] = None,
            difficulty_level: Optional[int] = None,
            word_type: Optional[str] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[Word]:
        """Search words by foreign word, local word, or example sentence"""
        query = db.query(Word).filter(
            or_(
                Word.foreign.ilike(f"%{search_term}%"),
                Word.local.ilike(f"%{search_term}%"),
                Word.example_sentence.ilike(f"%{search_term}%")
            )
        )

        if lesson_id:
            query = query.filter(Word.lesson_id == lesson_id)
        elif module_id:
            query = query.join(Lesson).filter(Lesson.module_id == module_id)
        elif course_id:
            query = query.join(Lesson).join(Module).filter(Module.course_id == course_id)
        elif learning_center_id:
            query = query.join(Lesson).join(Module).join(Course).filter(
                Course.learning_center_id == learning_center_id
            )

        if difficulty_level:
            query = query.filter(Word.difficulty_level == difficulty_level)

        if word_type:
            query = query.filter(Word.word_type == word_type)

        return query.filter(Word.is_active == True).options(
            joinedload(Word.lesson).joinedload(Lesson.module).joinedload(Module.course)
        ).offset(skip).limit(limit).all()

    def get_by_difficulty_level(
            self,
            db: Session,
            difficulty_level: int,
            course_id: Optional[int] = None,
            learning_center_id: Optional[int] = None,
            limit: Optional[int] = None
    ) -> List[Word]:
        """Get words by difficulty level"""
        query = db.query(Word).filter(Word.difficulty_level == difficulty_level)

        if course_id:
            query = query.join(Lesson).join(Module).filter(Module.course_id == course_id)
        elif learning_center_id:
            query = query.join(Lesson).join(Module).join(Course).filter(
                Course.learning_center_id == learning_center_id
            )

        query = query.filter(Word.is_active == True).order_by(func.random())

        if limit:
            query = query.limit(limit)

        return query.options(
            joinedload(Word.lesson).joinedload(Lesson.module)
        ).all()

    def get_random_words(
            self,
            db: Session,
            count: int,
            course_id: Optional[int] = None,
            learning_center_id: Optional[int] = None,
            difficulty_range: Optional[tuple] = None,
            exclude_ids: Optional[List[int]] = None,
            word_types: Optional[List[str]] = None
    ) -> List[Word]:
        """Get random words for practice"""
        query = db.query(Word).filter(Word.is_active == True)

        if course_id:
            query = query.join(Lesson).join(Module).filter(Module.course_id == course_id)
        elif learning_center_id:
            query = query.join(Lesson).join(Module).join(Course).filter(
                Course.learning_center_id == learning_center_id
            )

        if difficulty_range:
            min_diff, max_diff = difficulty_range
            query = query.filter(
                and_(
                    Word.difficulty_level >= min_diff,
                    Word.difficulty_level <= max_diff
                )
            )

        if exclude_ids:
            query = query.filter(~Word.id.in_(exclude_ids))

        if word_types:
            query = query.filter(Word.word_type.in_(word_types))

        return query.options(
            joinedload(Word.lesson).joinedload(Lesson.module)
        ).order_by(func.random()).limit(count).all()

    def get_words_by_type(
            self,
            db: Session,
            word_type: str,
            course_id: Optional[int] = None,
            learning_center_id: Optional[int] = None,
            limit: Optional[int] = None
    ) -> List[Word]:
        """Get words by grammatical type (noun, verb, adjective, etc.)"""
        query = db.query(Word).filter(
            and_(Word.word_type == word_type, Word.is_active == True)
        )

        if course_id:
            query = query.join(Lesson).join(Module).filter(Module.course_id == course_id)
        elif learning_center_id:
            query = query.join(Lesson).join(Module).join(Course).filter(
                Course.learning_center_id == learning_center_id
            )

        if limit:
            query = query.limit(limit)

        return query.options(
            joinedload(Word.lesson).joinedload(Lesson.module)
        ).order_by(Word.order_index).all()

    def get_words_without_audio(self, db: Session, course_id: Optional[int] = None,
                                learning_center_id: Optional[int] = None) -> List[Word]:
        """Get words that don't have audio URLs"""
        query = db.query(Word).filter(
            and_(
                or_(Word.audio_url.is_(None), Word.audio_url == ""),
                Word.is_active == True
            )
        )

        if course_id:
            query = query.join(Lesson).join(Module).filter(Module.course_id == course_id)
        elif learning_center_id:
            query = query.join(Lesson).join(Module).join(Course).filter(
                Course.learning_center_id == learning_center_id
            )

        return query.options(
            joinedload(Word.lesson).joinedload(Lesson.module)
        ).all()

    def get_words_with_audio(self, db: Session, course_id: Optional[int] = None,
                             learning_center_id: Optional[int] = None) -> List[Word]:
        """Get words that have audio URLs"""
        query = db.query(Word).filter(
            and_(
                Word.audio_url.isnot(None),
                Word.audio_url != "",
                Word.is_active == True
            )
        )

        if course_id:
            query = query.join(Lesson).join(Module).filter(Module.course_id == course_id)
        elif learning_center_id:
            query = query.join(Lesson).join(Module).join(Course).filter(
                Course.learning_center_id == learning_center_id
            )

        return query.options(
            joinedload(Word.lesson).joinedload(Lesson.module)
        ).all()

    def reorder_words(self, db: Session, word_orders: List[dict]) -> bool:
        """Reorder words within a lesson"""
        try:
            for order_data in word_orders:
                word = self.get(db, order_data["word_id"])
                if word:
                    word.order_index = order_data["order_index"]

            db.commit()
            return True
        except Exception:
            db.rollback()
            return False

    def bulk_update_audio_urls(self, db: Session, word_audio_map: dict) -> bool:
        """Bulk update audio URLs for words"""
        try:
            for word_id, audio_url in word_audio_map.items():
                word = self.get(db, int(word_id))
                if word:
                    word.audio_url = audio_url

            db.commit()
            return True
        except Exception:
            db.rollback()
            return False

    def bulk_update_difficulty(self, db: Session, word_difficulty_map: dict) -> bool:
        """Bulk update difficulty levels for words"""
        try:
            for word_id, difficulty_level in word_difficulty_map.items():
                word = self.get(db, int(word_id))
                if word and 1 <= difficulty_level <= 5:
                    word.difficulty_level = difficulty_level

            db.commit()
            return True
        except Exception:
            db.rollback()
            return False

    def get_word_statistics(self, db: Session, course_id: Optional[int] = None,
                            learning_center_id: Optional[int] = None) -> dict:
        """Get comprehensive word statistics"""
        base_query = db.query(Word).filter(Word.is_active == True)

        if course_id:
            base_query = base_query.join(Lesson).join(Module).filter(Module.course_id == course_id)
        elif learning_center_id:
            base_query = base_query.join(Lesson).join(Module).join(Course).filter(
                Course.learning_center_id == learning_center_id
            )

        total_words = base_query.count()

        # Words by difficulty
        difficulty_stats = base_query.with_entities(
            Word.difficulty_level,
            func.count(Word.id).label('count')
        ).group_by(Word.difficulty_level).all()

        # Words by type
        type_stats = base_query.filter(Word.word_type.isnot(None)).with_entities(
            Word.word_type,
            func.count(Word.id).label('count')
        ).group_by(Word.word_type).all()

        # Words with/without audio
        words_with_audio = base_query.filter(
            and_(Word.audio_url.isnot(None), Word.audio_url != "")
        ).count()

        # Average difficulty
        avg_difficulty = base_query.with_entities(
            func.avg(Word.difficulty_level)
        ).scalar() or 0.0

        return {
            "total_words": total_words,
            "average_difficulty": round(float(avg_difficulty), 2),
            "words_with_audio": words_with_audio,
            "words_without_audio": total_words - words_with_audio,
            "audio_coverage_percentage": round((words_with_audio / total_words * 100) if total_words > 0 else 0, 2),
            "difficulty_distribution": {f"level_{level}": count for level, count in difficulty_stats},
            "word_type_distribution": {word_type or "unspecified": count for word_type, count in type_stats}
        }

    def find_similar_words(
            self,
            db: Session,
            word_id: int,
            similarity_type: str = "foreign",
            limit: int = 10
    ) -> List[Word]:
        """Find words similar to a given word (basic implementation using LIKE)"""
        word = self.get(db, word_id)
        if not word:
            return []

        if similarity_type == "foreign":
            search_field = Word.foreign
            search_term = word.foreign
        elif similarity_type == "local":
            search_field = Word.local
            search_term = word.local
        else:  # both
            similar_words_foreign = self._find_similar_by_field(db, word_id, word.foreign, Word.foreign, limit // 2)
            similar_words_local = self._find_similar_by_field(db, word_id, word.local, Word.local, limit // 2)
            return similar_words_foreign + similar_words_local

        return self._find_similar_by_field(db, word_id, search_term, search_field, limit)

    def _find_similar_by_field(self, db: Session, word_id: int, search_term: str, search_field, limit: int) -> List[
        Word]:
        """Helper method to find similar words by a specific field"""
        similar_words = db.query(Word).filter(
            and_(
                Word.id != word_id,
                or_(
                    search_field.ilike(f"%{search_term[:3]}%"),  # First 3 characters
                    search_field.ilike(f"%{search_term[-3:]}%")  # Last 3 characters
                ),
                Word.is_active == True
            )
        ).options(
            joinedload(Word.lesson).joinedload(Lesson.module)
        ).limit(limit).all()

        return similar_words

    def get_words_for_practice(
            self,
            db: Session,
            difficulty_preference: str = "mixed",
            exclude_recent_ids: Optional[List[int]] = None,
            course_id: Optional[int] = None,
            learning_center_id: Optional[int] = None,
            limit: int = 20
    ) -> List[Word]:
        """Get words suitable for practice based on preferences"""
        query = db.query(Word).filter(Word.is_active == True)

        if course_id:
            query = query.join(Lesson).join(Module).filter(Module.course_id == course_id)
        elif learning_center_id:
            query = query.join(Lesson).join(Module).join(Course).filter(
                Course.learning_center_id == learning_center_id
            )

        if exclude_recent_ids:
            query = query.filter(~Word.id.in_(exclude_recent_ids))

        if difficulty_preference == "easy":
            query = query.filter(Word.difficulty_level.in_([1, 2]))
        elif difficulty_preference == "hard":
            query = query.filter(Word.difficulty_level.in_([4, 5]))
        elif difficulty_preference == "medium":
            query = query.filter(Word.difficulty_level == 3)
        # "mixed" includes all difficulties

        return query.options(
            joinedload(Word.lesson).joinedload(Lesson.module)
        ).order_by(func.random()).limit(limit).all()

    def get_lesson_completion_words(self, db: Session, lesson_id: int) -> Dict[str, Any]:
        """Get word statistics for lesson completion calculation"""
        words = self.get_by_lesson(db, lesson_id, active_only=True)

        total_words = len(words)
        total_points = sum(word.points_value for word in words)

        difficulty_breakdown = {}
        for word in words:
            level = word.difficulty_level
            if level not in difficulty_breakdown:
                difficulty_breakdown[level] = 0
            difficulty_breakdown[level] += 1

        return {
            "lesson_id": lesson_id,
            "total_words": total_words,
            "total_points": total_points,
            "average_difficulty": sum(w.difficulty_level for w in words) / total_words if total_words > 0 else 0,
            "difficulty_breakdown": difficulty_breakdown
        }

    def validate_word_uniqueness(self, db: Session, foreign: str, local: str, lesson_id: int,
                                 exclude_id: Optional[int] = None) -> bool:
        """Check if a word combination is unique within a lesson"""
        query = db.query(Word).filter(
            and_(
                Word.foreign == foreign,
                Word.local == local,
                Word.lesson_id == lesson_id
            )
        )

        if exclude_id:
            query = query.filter(Word.id != exclude_id)

        return query.first() is None
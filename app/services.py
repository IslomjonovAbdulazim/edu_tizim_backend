from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from .models import *
from .database import RedisService
from . import schemas


class AuthService:
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(
            User.email == email,
            User.is_active == True
        ).first()

    @staticmethod
    def get_user_by_phone(db: Session, phone: str) -> Optional[User]:
        return db.query(User).filter(
            User.phone == phone,
            User.is_active == True
        ).first()

    @staticmethod
    def verify_phone_telegram(db: Session, phone: str, telegram_id: str) -> Optional[User]:
        return db.query(User).filter(
            User.phone == phone,
            User.telegram_id == telegram_id,
            User.role == UserRole.STUDENT,
            User.is_active == True
        ).first()


class ContentService:
    @staticmethod
    def get_course_content(db: Session, center_id: int):
        """Get complete course structure with Redis caching"""
        cache_key = f"content:center:{center_id}"

        # Try cache first
        cached_content = RedisService.get_json(cache_key)
        if cached_content:
            return cached_content

        # Build content from database
        courses = db.query(Course).filter(
            Course.center_id == center_id,
            Course.is_active == True
        ).order_by(Course.created_at).all()

        content = []
        for course in courses:
            modules = db.query(Module).filter(
                Module.course_id == course.id,
                Module.is_active == True
            ).order_by(Module.order_index).all()

            course_data = {
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "modules": []
            }

            for module in modules:
                lessons = db.query(Lesson).filter(
                    Lesson.module_id == module.id,
                    Lesson.is_active == True
                ).order_by(Lesson.order_index).all()

                module_data = {
                    "id": module.id,
                    "title": module.title,
                    "description": module.description,
                    "lessons": []
                }

                for lesson in lessons:
                    words_count = db.query(Word).filter(
                        Word.lesson_id == lesson.id,
                        Word.is_active == True
                    ).count()

                    lesson_data = {
                        "id": lesson.id,
                        "title": lesson.title,
                        "description": lesson.description,
                        "words_count": words_count
                    }
                    module_data["lessons"].append(lesson_data)

                course_data["modules"].append(module_data)
            content.append(course_data)

        # Cache for 1 hour
        RedisService.set_json(cache_key, content, 3600)
        return content

    @staticmethod
    def get_lesson_words(db: Session, lesson_id: int):
        """Get lesson words with caching"""
        cache_key = f"words:lesson:{lesson_id}"

        # Try cache first
        cached_words = RedisService.get_json(cache_key)
        if cached_words:
            return cached_words

        words = db.query(Word).filter(
            Word.lesson_id == lesson_id,
            Word.is_active == True
        ).order_by(Word.order_index).all()

        word_data = [
            {
                "id": word.id,
                "word": word.word,
                "meaning": word.meaning,
                "definition": word.definition,
                "example_sentence": word.example_sentence,
                "image_url": word.image_url,
                "audio_url": word.audio_url
            } for word in words
        ]

        # Cache for 30 minutes
        RedisService.set_json(cache_key, word_data, 1800)
        return word_data

    @staticmethod
    def invalidate_center_cache(center_id: int):
        """Clear all cache for a center"""
        RedisService.clear_pattern(f"content:center:{center_id}")
        RedisService.clear_pattern(f"words:lesson:*")
        RedisService.clear_pattern(f"leaderboard:center:{center_id}*")


class ProgressService:
    @staticmethod
    def update_lesson_progress(db: Session, profile_id: int, lesson_id: int, percentage: int):
        """Update lesson progress and award coins"""
        progress = db.query(Progress).filter(
            Progress.profile_id == profile_id,
            Progress.lesson_id == lesson_id
        ).first()

        was_completed = progress.completed if progress else False

        if not progress:
            progress = Progress(
                profile_id=profile_id,
                lesson_id=lesson_id,
                percentage=percentage,
                completed=percentage >= 100
            )
            db.add(progress)
        else:
            progress.percentage = max(progress.percentage, percentage)  # Only increase
            progress.completed = progress.percentage >= 100
            progress.last_practiced = func.now()

        # Award coins for first completion
        if progress.percentage >= 100 and not was_completed:
            coin = Coin(
                profile_id=profile_id,
                amount=10,
                source="lesson_complete",
                source_id=lesson_id
            )
            db.add(coin)

        db.commit()

        # Clear leaderboard cache
        profile = db.query(LearningCenterProfile).filter(
            LearningCenterProfile.id == profile_id
        ).first()
        if profile:
            RedisService.clear_pattern(f"leaderboard:center:{profile.center_id}*")

    @staticmethod
    def update_word_progress(db: Session, profile_id: int, word_id: int, correct: bool):
        """Update word-level progress tracking"""
        progress = db.query(WordProgress).filter(
            WordProgress.profile_id == profile_id,
            WordProgress.word_id == word_id
        ).first()

        if not progress:
            progress = WordProgress(
                profile_id=profile_id,
                word_id=word_id,
                last_seven_attempts="",
                total_correct=0,
                total_attempts=0
            )
            db.add(progress)

        # Update attempts tracking
        attempts = progress.last_seven_attempts
        new_attempt = "1" if correct else "0"
        attempts = (attempts + new_attempt)[-7:]  # Keep last 7

        progress.last_seven_attempts = attempts
        progress.total_attempts += 1
        if correct:
            progress.total_correct += 1
        progress.last_practiced = func.now()

        db.commit()

    @staticmethod
    def get_weak_words(db: Session, profile_id: int, limit: int = 20) -> List[int]:
        """Get words that need more practice"""
        weak_words = db.query(WordProgress.word_id).filter(
            WordProgress.profile_id == profile_id,
            WordProgress.last_seven_attempts.like('%0%')  # Contains mistakes
        ).limit(limit).all()

        return [w[0] for w in weak_words]


class LeaderboardService:
    @staticmethod
    def get_center_leaderboard(db: Session, center_id: int, limit: int = 50) -> List[dict]:
        """Get center leaderboard with caching"""
        cache_key = f"leaderboard:center:{center_id}"

        # Try cache first
        cached_leaderboard = RedisService.get_json(cache_key)
        if cached_leaderboard:
            return cached_leaderboard[:limit]

        results = db.query(
            LearningCenterProfile.id,
            LearningCenterProfile.full_name,
            User.avatar,
            func.coalesce(func.sum(Coin.amount), 0).label('total_coins')
        ).outerjoin(
            Coin, Coin.profile_id == LearningCenterProfile.id
        ).join(
            User, User.id == LearningCenterProfile.user_id
        ).filter(
            LearningCenterProfile.center_id == center_id,
            LearningCenterProfile.is_active == True,
            LearningCenterProfile.role_in_center == UserRole.STUDENT
        ).group_by(
            LearningCenterProfile.id,
            LearningCenterProfile.full_name,
            User.avatar
        ).order_by(desc('total_coins')).limit(100).all()

        leaderboard = [
            {
                "profile_id": r[0],
                "full_name": r[1],
                "avatar": r[2],
                "total_coins": int(r[3])
            } for r in results
        ]

        # Cache for 5 minutes
        RedisService.set_json(cache_key, leaderboard, 300)
        return leaderboard[:limit]

    @staticmethod
    def get_group_leaderboard(db: Session, group_id: int) -> List[dict]:
        """Get group-specific leaderboard"""
        cache_key = f"leaderboard:group:{group_id}"

        cached_leaderboard = RedisService.get_json(cache_key)
        if cached_leaderboard:
            return cached_leaderboard

        results = db.query(
            LearningCenterProfile.id,
            LearningCenterProfile.full_name,
            User.avatar,
            func.coalesce(func.sum(Coin.amount), 0).label('total_coins')
        ).join(
            GroupMember, GroupMember.profile_id == LearningCenterProfile.id
        ).outerjoin(
            Coin, Coin.profile_id == LearningCenterProfile.id
        ).join(
            User, User.id == LearningCenterProfile.user_id
        ).filter(
            GroupMember.group_id == group_id,
            LearningCenterProfile.is_active == True
        ).group_by(
            LearningCenterProfile.id,
            LearningCenterProfile.full_name,
            User.avatar
        ).order_by(desc('total_coins')).all()

        leaderboard = [
            {
                "profile_id": r[0],
                "full_name": r[1],
                "avatar": r[2],
                "total_coins": int(r[3])
            } for r in results
        ]

        # Cache for 5 minutes
        RedisService.set_json(cache_key, leaderboard, 300)
        return leaderboard


class PaymentService:
    @staticmethod
    def add_payment(db: Session, payment_data: schemas.PaymentCreate, created_by: int):
        """Process payment and extend center subscription"""
        # Create payment record
        payment = Payment(
            center_id=payment_data.center_id,
            amount=payment_data.amount,
            days_added=payment_data.days_added,
            description=payment_data.description,
            created_by=created_by
        )
        db.add(payment)

        # Update learning center days
        center = db.query(LearningCenter).filter(
            LearningCenter.id == payment_data.center_id
        ).first()
        if center:
            center.days_remaining = max(0, center.days_remaining) + payment_data.days_added
            if center.days_remaining > 0:
                center.is_active = True

        db.commit()
        db.refresh(payment)
        return payment
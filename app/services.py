from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
import json
from models import *
from database import get_cache, set_cache, delete_cache, clear_cache_pattern
import schemas


class AuthService:
    @staticmethod
    def get_user_by_email(db: Session, email: str):
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_phone(db: Session, phone: str):
        return db.query(User).filter(User.phone == phone).first()

    @staticmethod
    def verify_phone_telegram(db: Session, phone: str, telegram_id: str):
        user = db.query(User).filter(
            User.phone == phone,
            User.telegram_id == telegram_id,
            User.role == UserRole.STUDENT
        ).first()
        return user


class ContentService:
    @staticmethod
    def get_course_content(db: Session, center_id: int):
        # Try cache first
        cache_key = f"course_content:{center_id}"
        cached = get_cache(cache_key)
        if cached:
            return json.loads(cached)

        courses = db.query(Course).filter(
            Course.center_id == center_id,
            Course.is_active == True
        ).all()

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
                    words = db.query(Word).filter(
                        Word.lesson_id == lesson.id,
                        Word.is_active == True
                    ).order_by(Word.order_index).all()

                    lesson_data = {
                        "id": lesson.id,
                        "title": lesson.title,
                        "description": lesson.description,
                        "words": [
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
                    }
                    module_data["lessons"].append(lesson_data)

                course_data["modules"].append(module_data)
            content.append(course_data)

        # Cache for 1 hour
        set_cache(cache_key, json.dumps(content, default=str), 3600)
        return content

    @staticmethod
    def invalidate_content_cache(center_id: int):
        clear_cache_pattern(f"course_content:{center_id}")


class ProgressService:
    @staticmethod
    def update_lesson_progress(db: Session, profile_id: int, lesson_id: int, percentage: int):
        progress = db.query(Progress).filter(
            Progress.profile_id == profile_id,
            Progress.lesson_id == lesson_id
        ).first()

        if not progress:
            progress = Progress(
                profile_id=profile_id,
                lesson_id=lesson_id,
                percentage=percentage,
                completed=percentage >= 100
            )
            db.add(progress)
        else:
            progress.percentage = percentage
            progress.completed = percentage >= 100
            progress.last_practiced = func.now()

        # Award coins for completion
        if percentage >= 100 and not progress.completed:
            coin = Coin(
                profile_id=profile_id,
                amount=10,  # 10 coins for lesson completion
                source="lesson",
                source_id=lesson_id
            )
            db.add(coin)

        db.commit()

        # Clear leaderboard cache
        profile = db.query(LearningCenterProfile).filter(
            LearningCenterProfile.id == profile_id
        ).first()
        if profile:
            clear_cache_pattern(f"leaderboard:{profile.center_id}*")

    @staticmethod
    def update_word_progress(db: Session, profile_id: int, word_id: int, correct: bool):
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

        # Update last 7 attempts
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
    def get_weak_words(db: Session, profile_id: int) -> List[int]:
        """Get words where user made mistakes in recent attempts"""
        weak_words = db.query(WordProgress.word_id).filter(
            WordProgress.profile_id == profile_id,
            WordProgress.last_seven_attempts.like('%0%')  # Has mistakes
        ).all()

        return [w[0] for w in weak_words]


class LeaderboardService:
    @staticmethod
    def get_center_leaderboard(db: Session, center_id: int) -> List[schemas.LeaderboardEntry]:
        cache_key = f"leaderboard:{center_id}"
        cached = get_cache(cache_key)
        if cached:
            return json.loads(cached)

        results = db.query(
            LearningCenterProfile.id,
            LearningCenterProfile.full_name,
            User.avatar,
            func.sum(Coin.amount).label('total_coins')
        ).join(
            Coin, Coin.profile_id == LearningCenterProfile.id
        ).join(
            User, User.id == LearningCenterProfile.user_id
        ).filter(
            LearningCenterProfile.center_id == center_id,
            LearningCenterProfile.is_active == True
        ).group_by(
            LearningCenterProfile.id,
            LearningCenterProfile.full_name,
            User.avatar
        ).order_by(desc('total_coins')).all()

        leaderboard = [
            schemas.LeaderboardEntry(
                profile_id=r[0],
                full_name=r[1],
                avatar=r[2],
                total_coins=r[3] or 0
            ) for r in results
        ]

        # Cache for 5 minutes
        set_cache(cache_key, json.dumps([l.dict() for l in leaderboard]), 300)
        return leaderboard

    @staticmethod
    def get_group_leaderboard(db: Session, group_id: int) -> List[schemas.LeaderboardEntry]:
        cache_key = f"leaderboard:group:{group_id}"
        cached = get_cache(cache_key)
        if cached:
            return json.loads(cached)

        results = db.query(
            LearningCenterProfile.id,
            LearningCenterProfile.full_name,
            User.avatar,
            func.sum(Coin.amount).label('total_coins')
        ).join(
            GroupMember, GroupMember.profile_id == LearningCenterProfile.id
        ).join(
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
            schemas.LeaderboardEntry(
                profile_id=r[0],
                full_name=r[1],
                avatar=r[2],
                total_coins=r[3] or 0
            ) for r in results
        ]

        # Cache for 5 minutes
        set_cache(cache_key, json.dumps([l.dict() for l in leaderboard]), 300)
        return leaderboard


class PaymentService:
    @staticmethod
    def add_payment(db: Session, payment_data: schemas.PaymentCreate, created_by: int):
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
            center.days_remaining += payment_data.days_added
            if center.days_remaining > 0:
                center.is_active = True

        db.commit()
        return payment
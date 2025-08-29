from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models import UserRole
from app.schemas import (
    ProgressCreate, ProgressUpdate, ProgressResponse,
    QuizSessionCreate, QuizSessionResponse, QuizSubmission, QuizResult,
    WeakWordResponse, WeakWordWithDetails, UserLearningStats, LessonStats
)
from app.services.base import BaseService


class LearningService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)

    # Progress Management
    def get_user_progress(self, user_id: int, requester_id: int) -> Dict[str, Any]:
        """Get all progress records for user"""
        # Permission check: users can view own progress, teachers/admin can view their center's students
        requester = self.repos.user.get(requester_id)
        user = self.repos.user.get(user_id)

        if not requester or not user:
            return self._format_error_response("User not found")

        can_view = (
                user_id == requester_id or  # Own progress
                requester.has_role(UserRole.SUPER_ADMIN) or  # Super admin
                (requester.learning_center_id == user.learning_center_id and
                 requester.has_any_role([UserRole.ADMIN, UserRole.TEACHER, UserRole.GROUP_MANAGER]))
        )

        if not can_view:
            return self._format_error_response("Insufficient permissions")

        progress_records = self.repos.progress.get_user_progress(user_id)
        progress_data = [ProgressResponse.from_orm(p) for p in progress_records]

        return self._format_success_response(progress_data)

    def get_lesson_progress(self, user_id: int, lesson_id: int) -> Dict[str, Any]:
        """Get specific lesson progress for user"""
        user = self.repos.user.get(user_id)
        lesson = self.repos.lesson.get(lesson_id)

        if not user or not lesson:
            return self._format_error_response("User or lesson not found")

        # Check if user can access this lesson
        if user.learning_center_id != lesson.module.course.learning_center_id:
            return self._format_error_response("User cannot access this lesson")

        progress = self.repos.progress.get_by_user_lesson(user_id, lesson_id)

        if not progress:
            # Create initial progress record
            progress = self.repos.progress.create({
                "user_id": user_id,
                "lesson_id": lesson_id,
                "completion_percentage": 0.0,
                "points": 0,
                "total_attempts": 0,
                "correct_answers": 0
            })

        return self._format_success_response(ProgressResponse.from_orm(progress))

    def update_lesson_progress(self, user_id: int, lesson_id: int, completion_percentage: float) -> Dict[str, Any]:
        """Update lesson progress based on quiz results"""
        if not 0 <= completion_percentage <= 100:
            return self._format_error_response("Completion percentage must be between 0 and 100")

        user = self.repos.user.get(user_id)
        lesson = self.repos.lesson.get(lesson_id)

        if not user or not lesson:
            return self._format_error_response("User or lesson not found")

        # Check access
        if user.learning_center_id != lesson.module.course.learning_center_id:
            return self._format_error_response("User cannot access this lesson")

        # Update progress
        progress = self.repos.progress.update_progress(user_id, lesson_id, completion_percentage)

        return self._format_success_response({
            "progress": ProgressResponse.from_orm(progress),
            "points_gained": int(completion_percentage - (progress.completion_percentage - completion_percentage)),
            "is_completed": progress.is_completed
        })

    # Quiz Session Management
    def start_quiz_session(self, user_id: int, lesson_id: int) -> Dict[str, Any]:
        """Start new quiz session"""
        user = self.repos.user.get(user_id)
        lesson = self.repos.lesson.get(lesson_id)

        if not user or not lesson:
            return self._format_error_response("User or lesson not found")

        # Check access
        if user.learning_center_id != lesson.module.course.learning_center_id:
            return self._format_error_response("User cannot access this lesson")

        # Check if user already has active session
        active_session = self.repos.quiz_session.get_active_session(user_id, lesson_id)
        if active_session:
            return self._format_success_response(
                QuizSessionResponse.from_orm(active_session),
                "Resuming existing quiz session"
            )

        # Create new session
        session = self.repos.quiz_session.create_session(user_id, lesson_id)

        return self._format_success_response(
            QuizSessionResponse.from_orm(session),
            "Quiz session started"
        )

    def submit_quiz(self, quiz_data: QuizSubmission) -> Dict[str, Any]:
        """Submit quiz results and update progress"""
        user = self.repos.user.get(quiz_data.user_id)
        lesson = self.repos.lesson.get(quiz_data.lesson_id)

        if not user or not lesson:
            return self._format_error_response("User or lesson not found")

        # Check access
        if user.learning_center_id != lesson.module.course.learning_center_id:
            return self._format_error_response("User cannot access this lesson")

        try:
            # Get or create active session
            session = self.repos.quiz_session.get_active_session(quiz_data.user_id, quiz_data.lesson_id)
            if not session:
                session = self.repos.quiz_session.create_session(quiz_data.user_id, quiz_data.lesson_id)

            # Complete the session with results
            completed_session = self.repos.quiz_session.complete_session(session.id, quiz_data.word_results)

            # Update lesson progress (completion percentage = accuracy)
            completion_percentage = completed_session.completion_percentage
            progress = self.repos.progress.update_progress(
                quiz_data.user_id,
                quiz_data.lesson_id,
                completion_percentage
            )

            # Update weak words
            weak_words = self.repos.weak_word.process_quiz_results(
                quiz_data.user_id,
                quiz_data.word_results
            )

            # Calculate points gained (points = completion percentage)
            points_gained = int(completion_percentage)

            quiz_result = QuizResult(
                points_earned=points_gained,
                completion_percentage=completion_percentage,
                accuracy=completed_session.accuracy,
                total_questions=completed_session.total_questions,
                correct_answers=completed_session.correct_answers
            )

            return self._format_success_response({
                "quiz_result": quiz_result,
                "session": QuizSessionResponse.from_orm(completed_session),
                "progress": ProgressResponse.from_orm(progress),
                "weak_words_updated": len(weak_words)
            }, "Quiz submitted successfully")

        except Exception as e:
            return self._format_error_response(f"Failed to submit quiz: {str(e)}")

    def get_user_quiz_history(self, user_id: int, limit: int = 20) -> Dict[str, Any]:
        """Get user's quiz session history"""
        sessions = self.repos.quiz_session.get_recent_sessions(user_id, limit)
        sessions_data = [QuizSessionResponse.from_orm(s) for s in sessions]

        return self._format_success_response(sessions_data)

    # Weak Words Management
    def get_user_weak_words(self, user_id: int, requester_id: int) -> Dict[str, Any]:
        """Get user's weak words with word details"""
        # Permission check
        if user_id != requester_id:
            requester = self.repos.user.get(requester_id)
            user = self.repos.user.get(user_id)

            if not requester or not user:
                return self._format_error_response("User not found")

            can_view = (
                    requester.has_role(UserRole.SUPER_ADMIN) or
                    (requester.learning_center_id == user.learning_center_id and
                     requester.has_any_role([UserRole.ADMIN, UserRole.TEACHER]))
            )

            if not can_view:
                return self._format_error_response("Insufficient permissions")

        # Get weak words with word details
        weak_words = self.repos.weak_word.get_user_weak_words(user_id)
        weak_words_data = []

        for weak_word in weak_words:
            word_detail = WeakWordWithDetails.from_orm(weak_word)
            word_detail.foreign_form = weak_word.word.foreign_form
            word_detail.native_form = weak_word.word.native_form
            word_detail.example_sentence = weak_word.word.example_sentence
            word_detail.audio_url = weak_word.word.audio_url
            weak_words_data.append(word_detail)

        return self._format_success_response(weak_words_data)

    def get_practice_words(self, user_id: int, limit: int = 20) -> Dict[str, Any]:
        """Get words for practice (prioritize weak words)"""
        practice_words = self.repos.weak_word.get_practice_words(user_id, limit)

        if not practice_words:
            return self._format_success_response([], "No practice words available")

        practice_data = []
        for weak_word in practice_words:
            word_detail = WeakWordWithDetails.from_orm(weak_word)
            word_detail.foreign_form = weak_word.word.foreign_form
            word_detail.native_form = weak_word.word.native_form
            word_detail.example_sentence = weak_word.word.example_sentence
            word_detail.audio_url = weak_word.word.audio_url
            practice_data.append(word_detail)

        return self._format_success_response(practice_data, f"Found {len(practice_data)} words for practice")

    def get_words_by_strength(self, user_id: int, strength: str) -> Dict[str, Any]:
        """Get user's words by strength level (weak, medium, strong)"""
        if strength not in ["weak", "medium", "strong"]:
            return self._format_error_response("Invalid strength level. Use: weak, medium, strong")

        weak_words = self.repos.weak_word.get_weak_words_by_strength(user_id, strength)
        weak_words_data = []

        for weak_word in weak_words:
            word_detail = WeakWordWithDetails.from_orm(weak_word)
            word_detail.foreign_form = weak_word.word.foreign_form
            word_detail.native_form = weak_word.word.native_form
            word_detail.example_sentence = weak_word.word.example_sentence
            word_detail.audio_url = weak_word.word.audio_url
            weak_words_data.append(word_detail)

        return self._format_success_response(weak_words_data)

    # Learning Analytics
    def get_user_learning_stats(self, user_id: int, requester_id: int) -> Dict[str, Any]:
        """Get comprehensive learning statistics for user"""
        # Permission check
        if user_id != requester_id:
            requester = self.repos.user.get(requester_id)
            user = self.repos.user.get(user_id)

            if not requester or not user:
                return self._format_error_response("User not found")

            can_view = (
                    requester.has_role(UserRole.SUPER_ADMIN) or
                    (requester.learning_center_id == user.learning_center_id and
                     requester.has_any_role([UserRole.ADMIN, UserRole.TEACHER, UserRole.GROUP_MANAGER]))
            )

            if not can_view:
                return self._format_error_response("Insufficient permissions")

        # Get statistics
        progress_records = self.repos.progress.get_user_progress(user_id)
        completed_lessons = [p for p in progress_records if p.is_completed]

        total_points = sum(p.points for p in progress_records)
        total_attempts = sum(p.total_attempts for p in progress_records)
        total_correct = sum(p.correct_answers for p in progress_records)

        average_accuracy = (total_correct / total_attempts * 100) if total_attempts > 0 else 0
        completion_rate = (len(completed_lessons) / len(progress_records) * 100) if progress_records else 0

        weak_words_count = self.repos.weak_word.get_weak_words_count(user_id)
        strong_words_count = self.repos.weak_word.get_mastered_words_count(user_id)

        stats = UserLearningStats(
            user_id=user_id,
            total_lessons=len(progress_records),
            completed_lessons=len(completed_lessons),
            completion_rate=completion_rate,
            total_points=total_points,
            average_accuracy=average_accuracy,
            weak_words_count=weak_words_count,
            strong_words_count=strong_words_count
        )

        return self._format_success_response(stats)

    def get_lesson_stats(self, lesson_id: int, requester_id: int) -> Dict[str, Any]:
        """Get lesson statistics across all users"""
        lesson = self.repos.lesson.get(lesson_id)
        if not lesson:
            return self._format_error_response("Lesson not found")

        # Permission check
        if not self._check_permissions(requester_id, [UserRole.TEACHER, UserRole.CONTENT_MANAGER, UserRole.ADMIN,
                                                      UserRole.SUPER_ADMIN], lesson.module.course.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        # Get lesson progress records
        progress_records = self.repos.progress.get_lesson_progress(lesson_id)
        quiz_sessions = self.repos.quiz_session.get_lesson_sessions(lesson_id)

        total_attempts = len(progress_records)
        completed = len([p for p in progress_records if p.is_completed])
        completion_rate = (completed / total_attempts * 100) if total_attempts > 0 else 0

        # Calculate average accuracy from quiz sessions
        completed_sessions = [s for s in quiz_sessions if s.is_completed]
        average_accuracy = sum(s.accuracy for s in completed_sessions) / len(
            completed_sessions) if completed_sessions else 0

        # Find difficult words (words with low success rate)
        word_stats = {}
        for session in completed_sessions:
            if session.quiz_results:
                for word_id, is_correct in session.quiz_results.items():
                    word_id = int(word_id)
                    if word_id not in word_stats:
                        word_stats[word_id] = {"correct": 0, "total": 0}
                    word_stats[word_id]["total"] += 1
                    if is_correct:
                        word_stats[word_id]["correct"] += 1

        # Find words with success rate < 60%
        difficult_words = []
        for word_id, stats in word_stats.items():
            success_rate = (stats["correct"] / stats["total"]) * 100
            if success_rate < 60:
                difficult_words.append(word_id)

        lesson_stats = LessonStats(
            lesson_id=lesson_id,
            total_attempts=total_attempts,
            completion_rate=completion_rate,
            average_accuracy=average_accuracy,
            difficult_words=difficult_words
        )

        return self._format_success_response(lesson_stats)

    def reset_user_progress(self, user_id: int, lesson_id: int, requester_id: int) -> Dict[str, Any]:
        """Reset user progress for specific lesson (admin only)"""
        if not self._check_permissions(requester_id, [UserRole.ADMIN, UserRole.SUPER_ADMIN]):
            return self._format_error_response("Admin access required")

        progress = self.repos.progress.get_by_user_lesson(user_id, lesson_id)
        if not progress:
            return self._format_error_response("Progress record not found")

        # Reset progress
        reset_progress = self.repos.progress.update(progress.id, {
            "completion_percentage": 0.0,
            "points": 0,
            "is_completed": False,
            "total_attempts": 0,
            "correct_answers": 0,
            "last_attempt_at": None
        })

        return self._format_success_response(
            ProgressResponse.from_orm(reset_progress),
            "User progress reset successfully"
        )
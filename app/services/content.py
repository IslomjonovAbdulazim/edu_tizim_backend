from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.user import UserRole
from app.schemas.content import (
    CourseCreate, CourseUpdate, CourseResponse,
    ModuleCreate, ModuleUpdate, ModuleResponse,
    LessonCreate, LessonUpdate, LessonResponse,
    WordCreate, WordUpdate, WordResponse, WordBulkCreate
)
from app.services.base import BaseService


class ContentService(BaseService):
    """Content service for managing educational content hierarchy"""

    def __init__(self, db: Session):
        super().__init__(db)

    # Course Management
    def create_course(self, course_data: CourseCreate, creator_id: int) -> Dict[str, Any]:
        """Create new course"""
        # Permission check
        if not self._check_permissions(
            creator_id,
            [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
            course_data.learning_center_id
        ):
            return self._format_error_response("Content manager access required")

        # Verify learning center exists and is active
        if not self._check_center_active(course_data.learning_center_id):
            return self._format_error_response("Learning center not found or inactive")

        try:
            course = self.repos.course.create(course_data.dict())
            return self._format_success_response(
                CourseResponse.from_orm(course),
                "Course created successfully"
            )

        except Exception as e:
            return self._format_error_response(f"Failed to create course: {str(e)}")

    def get_course_with_content(self, course_id: int, requester_id: int) -> Dict[str, Any]:
        """Get course with full content hierarchy"""
        course = self.repos.course.get_full_content(course_id)
        if not course:
            return self._format_error_response("Course not found")

        # Permission check - users can view courses from their learning center
        if not self._validate_learning_center_access(requester_id, course.learning_center_id):
            return self._format_error_response("Access denied to this course")

        return self._format_success_response({
            "id": course.id,
            "name": course.name,
            "description": course.description,
            "level": course.level,
            "modules": [
                {
                    "id": module.id,
                    "title": module.title,
                    "description": module.description,
                    "lessons": [
                        {
                            "id": lesson.id,
                            "title": lesson.title,
                            "description": lesson.description,
                            "words_count": len(lesson.words)
                        }
                        for lesson in module.lessons
                    ]
                }
                for module in course.modules
            ]
        })

    def update_course(self, course_id: int, update_data: CourseUpdate, updater_id: int) -> Dict[str, Any]:
        """Update course"""
        course = self.repos.course.get(course_id)
        if not course:
            return self._format_error_response("Course not found")

        if not self._check_permissions(
            updater_id,
            [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
            course.learning_center_id
        ):
            return self._format_error_response("Insufficient permissions")

        try:
            updated_course = self.repos.course.update(course_id, update_data.dict(exclude_unset=True))
            return self._format_success_response(
                CourseResponse.from_orm(updated_course),
                "Course updated successfully"
            )

        except Exception as e:
            return self._format_error_response(f"Failed to update course: {str(e)}")

    def get_courses_by_center(self, learning_center_id: int, requester_id: int) -> Dict[str, Any]:
        """Get all courses for learning center"""
        if not self._validate_learning_center_access(requester_id, learning_center_id):
            return self._format_error_response("Access denied")

        courses = self.repos.course.get_active_by_center(learning_center_id)
        courses_data = []

        for course in courses:
            stats = self.repos.course.get_course_stats(course.id)
            course_data = CourseResponse.from_orm(course)
            course_data.total_modules = stats.get("total_modules", 0)
            course_data.total_lessons = stats.get("total_lessons", 0)
            course_data.total_words = stats.get("total_words", 0)
            courses_data.append(course_data)

        return self._format_success_response(courses_data)

    # Module Management
    def create_module(self, module_data: ModuleCreate, creator_id: int) -> Dict[str, Any]:
        """Create new module"""
        course = self.repos.course.get(module_data.course_id)
        if not course:
            return self._format_error_response("Course not found")

        if not self._check_permissions(
            creator_id,
            [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
            course.learning_center_id
        ):
            return self._format_error_response("Insufficient permissions")

        try:
            module = self.repos.module.create(module_data.dict())
            return self._format_success_response(
                ModuleResponse.from_orm(module),
                "Module created successfully"
            )

        except Exception as e:
            return self._format_error_response(f"Failed to create module: {str(e)}")

    def get_module_with_content(self, module_id: int, requester_id: int) -> Dict[str, Any]:
        """Get module with lessons and words"""
        module = self.repos.module.get_full_content(module_id)
        if not module:
            return self._format_error_response("Module not found")

        if not self._validate_learning_center_access(requester_id, module.course.learning_center_id):
            return self._format_error_response("Access denied")

        return self._format_success_response({
            "id": module.id,
            "title": module.title,
            "description": module.description,
            "course_id": module.course_id,
            "lessons": [
                {
                    "id": lesson.id,
                    "title": lesson.title,
                    "description": lesson.description,
                    "content": lesson.content,
                    "words": [
                        {
                            "id": word.id,
                            "foreign_form": word.foreign_form,
                            "native_form": word.native_form,
                            "example_sentence": word.example_sentence,
                            "audio_url": word.audio_url,
                            "image_url": word.image_url
                        }
                        for word in lesson.words
                    ]
                }
                for lesson in module.lessons
            ]
        })

    # Lesson Management
    def create_lesson(self, lesson_data: LessonCreate, creator_id: int) -> Dict[str, Any]:
        """Create new lesson"""
        module = self.repos.module.get(lesson_data.module_id)
        if not module:
            return self._format_error_response("Module not found")

        if not self._check_permissions(
            creator_id,
            [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
            module.course.learning_center_id
        ):
            return self._format_error_response("Insufficient permissions")

        try:
            lesson = self.repos.lesson.create(lesson_data.dict())
            return self._format_success_response(
                LessonResponse.from_orm(lesson),
                "Lesson created successfully"
            )

        except Exception as e:
            return self._format_error_response(f"Failed to create lesson: {str(e)}")

    def get_lesson_with_words(self, lesson_id: int, requester_id: int) -> Dict[str, Any]:
        """Get lesson with all words for learning/quiz"""
        lesson = self.repos.lesson.get_with_words(lesson_id)
        if not lesson:
            return self._format_error_response("Lesson not found")

        if not self._validate_learning_center_access(requester_id, lesson.module.course.learning_center_id):
            return self._format_error_response("Access denied")

        return self._format_success_response({
            "id": lesson.id,
            "title": lesson.title,
            "description": lesson.description,
            "content": lesson.content,
            "module_id": lesson.module_id,
            "words": [
                WordResponse.from_orm(word) for word in lesson.words
            ]
        })

    def get_next_lesson(self, current_lesson_id: int, requester_id: int) -> Dict[str, Any]:
        """Get next lesson in sequence"""
        current_lesson = self.repos.lesson.get(current_lesson_id)
        if not current_lesson:
            return self._format_error_response("Current lesson not found")

        if not self._validate_learning_center_access(requester_id, current_lesson.module.course.learning_center_id):
            return self._format_error_response("Access denied")

        next_lesson = self.repos.lesson.get_next_lesson(current_lesson_id)
        if not next_lesson:
            return self._format_success_response(None, "No more lessons available")

        return self._format_success_response(LessonResponse.from_orm(next_lesson))

    # Word Management
    def create_word(self, word_data: WordCreate, creator_id: int) -> Dict[str, Any]:
        """Create new word"""
        lesson = self.repos.lesson.get(word_data.lesson_id)
        if not lesson:
            return self._format_error_response("Lesson not found")

        if not self._check_permissions(
            creator_id,
            [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
            lesson.module.course.learning_center_id
        ):
            return self._format_error_response("Insufficient permissions")

        # Check for duplicate words in the same lesson
        if self.repos.word.duplicate_word_check(word_data.lesson_id, word_data.foreign_form):
            return self._format_error_response("Word already exists in this lesson")

        try:
            word = self.repos.word.create(word_data.dict())
            return self._format_success_response(
                WordResponse.from_orm(word),
                "Word created successfully"
            )

        except Exception as e:
            return self._format_error_response(f"Failed to create word: {str(e)}")

    def bulk_create_words(self, bulk_data: WordBulkCreate, creator_id: int) -> Dict[str, Any]:
        """Create multiple words for a lesson"""
        lesson = self.repos.lesson.get(bulk_data.lesson_id)
        if not lesson:
            return self._format_error_response("Lesson not found")

        if not self._check_permissions(
            creator_id,
            [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
            lesson.module.course.learning_center_id
        ):
            return self._format_error_response("Insufficient permissions")

        try:
            words_data = [word.dict() for word in bulk_data.words]
            words = self.repos.word.bulk_create_words(bulk_data.lesson_id, words_data)
            words_response = [WordResponse.from_orm(w) for w in words]

            return self._format_success_response(
                words_response,
                f"Successfully created {len(words)} words"
            )

        except Exception as e:
            return self._format_error_response(f"Failed to create words: {str(e)}")

    def search_words(self, query: str, learning_center_id: int, requester_id: int, search_in: str = "both") -> Dict[str, Any]:
        """Search words by foreign/native form or example"""
        if not self._validate_learning_center_access(requester_id, learning_center_id):
            return self._format_error_response("Access denied")

        words = self.repos.word.search_words(learning_center_id, query, search_in)
        words_data = [WordResponse.from_orm(w) for w in words]

        return self._format_success_response({
            "words": words_data,
            "total_found": len(words_data),
            "query": query,
            "search_in": search_in
        })

    def get_random_words_for_quiz(self, lesson_id: int, count: int, requester_id: int) -> Dict[str, Any]:
        """Get random words from lesson for quiz"""
        lesson = self.repos.lesson.get(lesson_id)
        if not lesson:
            return self._format_error_response("Lesson not found")

        if not self._validate_learning_center_access(requester_id, lesson.module.course.learning_center_id):
            return self._format_error_response("Access denied")

        words = self.repos.word.get_random_words(lesson_id, count)
        words_data = [WordResponse.from_orm(w) for w in words]

        return self._format_success_response({
            "words": words_data,
            "count": len(words_data),
            "lesson_id": lesson_id
        })

    def get_content_statistics(self, learning_center_id: int, requester_id: int) -> Dict[str, Any]:
        """Get content statistics for learning center"""
        if not self._check_permissions(
            requester_id,
            [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
            learning_center_id
        ):
            return self._format_error_response("Insufficient permissions")

        # Get overall stats
        courses = self.repos.course.get_by_center(learning_center_id)
        word_stats = self.repos.word.get_word_stats(learning_center_id)

        total_modules = sum(
            self.repos.course.get_course_stats(course.id).get("total_modules", 0)
            for course in courses
        )
        total_lessons = sum(
            self.repos.course.get_course_stats(course.id).get("total_lessons", 0)
            for course in courses
        )

        stats = {
            "learning_center_id": learning_center_id,
            "total_courses": len(courses),
            "active_courses": len([c for c in courses if c.is_active]),
            "total_modules": total_modules,
            "total_lessons": total_lessons,
            **word_stats
        }

        return self._format_success_response(stats)

    def reorder_content(self, content_type: str, parent_id: int, order: list, requester_id: int) -> Dict[str, Any]:
        """Reorder content items (courses, modules, lessons, words)"""
        # Permission check based on content type
        if content_type == "courses":
            if not self._check_permissions(requester_id, [UserRole.ADMIN, UserRole.SUPER_ADMIN], parent_id):
                return self._format_error_response("Admin access required")
            success = self.repos.course.reorder_courses(parent_id, order)

        elif content_type == "modules":
            course = self.repos.course.get(parent_id)
            if not course:
                return self._format_error_response("Course not found")
            if not self._check_permissions(
                requester_id,
                [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                course.learning_center_id
            ):
                return self._format_error_response("Insufficient permissions")
            success = self.repos.module.reorder_modules(parent_id, order)

        elif content_type == "lessons":
            module = self.repos.module.get(parent_id)
            if not module:
                return self._format_error_response("Module not found")
            if not self._check_permissions(
                requester_id,
                [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                module.course.learning_center_id
            ):
                return self._format_error_response("Insufficient permissions")
            success = self.repos.lesson.reorder_lessons(parent_id, order)

        elif content_type == "words":
            lesson = self.repos.lesson.get(parent_id)
            if not lesson:
                return self._format_error_response("Lesson not found")
            if not self._check_permissions(
                requester_id,
                [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                lesson.module.course.learning_center_id
            ):
                return self._format_error_response("Insufficient permissions")
            success = self.repos.word.reorder_words(parent_id, order)

        else:
            return self._format_error_response("Invalid content type")

        if success:
            return self._format_success_response(message=f"{content_type.title()} reordered successfully")
        else:
            return self._format_error_response(f"Failed to reorder {content_type}")
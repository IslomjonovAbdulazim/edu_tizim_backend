from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models import UserRole
from app.schemas import (
    CourseCreate, CourseUpdate, CourseResponse, CourseWithModules, CourseWithFullContent,
    ModuleCreate, ModuleUpdate, ModuleResponse, ModuleWithLessons, ModuleWithFullContent,
    LessonCreate, LessonUpdate, LessonResponse, LessonWithWords,
    WordCreate, WordUpdate, WordResponse, WordBulkCreate
)
from app.services.base import BaseService


class ContentService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)

    # Course Management
    def create_course(self, course_data: CourseCreate, creator_id: int) -> Dict[str, Any]:
        """Create new course"""
        if not self._check_permissions(creator_id, [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN]):
            return self._format_error_response("Content manager, admin, or super admin access required")

        creator = self.repos.user.get(creator_id)

        # If not super admin, ensure creating for own learning center
        if not creator.has_role(UserRole.SUPER_ADMIN):
            if course_data.learning_center_id != creator.learning_center_id:
                return self._format_error_response("Can only create courses for your own learning center")

        # Verify learning center exists
        learning_center = self.repos.learning_center.get(course_data.learning_center_id)
        if not learning_center:
            return self._format_error_response("Learning center not found")

        try:
            course = self.repos.course.create(course_data.dict())
            return self._format_success_response(
                CourseResponse.from_orm(course),
                "Course created successfully"
            )
        except Exception as e:
            return self._format_error_response(f"Failed to create course: {str(e)}")

    def update_course(self, course_id: int, update_data: CourseUpdate, updater_id: int) -> Dict[str, Any]:
        """Update course"""
        course = self.repos.course.get(course_id)
        if not course:
            return self._format_error_response("Course not found")

        if not self._check_permissions(updater_id, [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       course.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        update_dict = update_data.dict(exclude_unset=True)
        updated_course = self.repos.course.update(course_id, update_dict)

        return self._format_success_response(
            CourseResponse.from_orm(updated_course),
            "Course updated successfully"
        )

    def get_course_with_content(self, course_id: int, requester_id: int) -> Dict[str, Any]:
        """Get course with full content hierarchy"""
        course = self.repos.course.get_full_content(course_id)
        if not course:
            return self._format_error_response("Course not found")

        # Permission check - users can view courses from their learning center
        if not self._check_permissions(requester_id,
                                       [UserRole.STUDENT, UserRole.TEACHER, UserRole.CONTENT_MANAGER, UserRole.ADMIN,
                                        UserRole.SUPER_ADMIN], course.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        course_data = CourseWithFullContent.from_orm(course)
        return self._format_success_response(course_data)

    def get_courses_by_center(self, learning_center_id: int, requester_id: int) -> Dict[str, Any]:
        """Get all courses for learning center"""
        if not self._check_permissions(requester_id,
                                       [UserRole.STUDENT, UserRole.TEACHER, UserRole.CONTENT_MANAGER, UserRole.ADMIN,
                                        UserRole.SUPER_ADMIN], learning_center_id):
            return self._format_error_response("Insufficient permissions")

        courses = self.repos.course.get_active_by_center(learning_center_id)
        courses_data = [CourseResponse.from_orm(c) for c in courses]

        return self._format_success_response(courses_data)

    # Module Management
    def create_module(self, module_data: ModuleCreate, creator_id: int) -> Dict[str, Any]:
        """Create new module"""
        course = self.repos.course.get(module_data.course_id)
        if not course:
            return self._format_error_response("Course not found")

        if not self._check_permissions(creator_id, [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       course.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        try:
            module = self.repos.module.create(module_data.dict())
            return self._format_success_response(
                ModuleResponse.from_orm(module),
                "Module created successfully"
            )
        except Exception as e:
            return self._format_error_response(f"Failed to create module: {str(e)}")

    def update_module(self, module_id: int, update_data: ModuleUpdate, updater_id: int) -> Dict[str, Any]:
        """Update module"""
        module = self.repos.module.get(module_id)
        if not module:
            return self._format_error_response("Module not found")

        if not self._check_permissions(updater_id, [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       module.course.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        update_dict = update_data.dict(exclude_unset=True)
        updated_module = self.repos.module.update(module_id, update_dict)

        return self._format_success_response(
            ModuleResponse.from_orm(updated_module),
            "Module updated successfully"
        )

    def get_module_with_content(self, module_id: int, requester_id: int) -> Dict[str, Any]:
        """Get module with lessons and words"""
        module = self.repos.module.get_full_content(module_id)
        if not module:
            return self._format_error_response("Module not found")

        if not self._check_permissions(requester_id,
                                       [UserRole.STUDENT, UserRole.TEACHER, UserRole.CONTENT_MANAGER, UserRole.ADMIN,
                                        UserRole.SUPER_ADMIN], module.course.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        module_data = ModuleWithFullContent.from_orm(module)
        return self._format_success_response(module_data)

    # Lesson Management
    def create_lesson(self, lesson_data: LessonCreate, creator_id: int) -> Dict[str, Any]:
        """Create new lesson"""
        module = self.repos.module.get(lesson_data.module_id)
        if not module:
            return self._format_error_response("Module not found")

        if not self._check_permissions(creator_id, [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       module.course.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        try:
            lesson = self.repos.lesson.create(lesson_data.dict())
            return self._format_success_response(
                LessonResponse.from_orm(lesson),
                "Lesson created successfully"
            )
        except Exception as e:
            return self._format_error_response(f"Failed to create lesson: {str(e)}")

    def update_lesson(self, lesson_id: int, update_data: LessonUpdate, updater_id: int) -> Dict[str, Any]:
        """Update lesson"""
        lesson = self.repos.lesson.get(lesson_id)
        if not lesson:
            return self._format_error_response("Lesson not found")

        if not self._check_permissions(updater_id, [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       lesson.module.course.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        update_dict = update_data.dict(exclude_unset=True)
        updated_lesson = self.repos.lesson.update(lesson_id, update_dict)

        return self._format_success_response(
            LessonResponse.from_orm(updated_lesson),
            "Lesson updated successfully"
        )

    def get_lesson_with_words(self, lesson_id: int, requester_id: int) -> Dict[str, Any]:
        """Get lesson with all words"""
        lesson = self.repos.lesson.get_with_words(lesson_id)
        if not lesson:
            return self._format_error_response("Lesson not found")

        if not self._check_permissions(requester_id,
                                       [UserRole.STUDENT, UserRole.TEACHER, UserRole.CONTENT_MANAGER, UserRole.ADMIN,
                                        UserRole.SUPER_ADMIN], lesson.module.course.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        lesson_data = LessonWithWords.from_orm(lesson)
        return self._format_success_response(lesson_data)

    def get_next_lesson(self, current_lesson_id: int, user_id: int) -> Dict[str, Any]:
        """Get next lesson in sequence for user"""
        current_lesson = self.repos.lesson.get(current_lesson_id)
        if not current_lesson:
            return self._format_error_response("Current lesson not found")

        # Check user access to current lesson
        if not self._check_permissions(user_id, [UserRole.STUDENT, UserRole.TEACHER],
                                       current_lesson.module.course.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        next_lesson = self.repos.lesson.get_next_lesson(current_lesson_id)
        if not next_lesson:
            return self._format_success_response(None, "No more lessons available")

        lesson_data = LessonResponse.from_orm(next_lesson)
        return self._format_success_response(lesson_data, "Next lesson found")

    # Word Management
    def create_word(self, word_data: WordCreate, creator_id: int) -> Dict[str, Any]:
        """Create new word"""
        lesson = self.repos.lesson.get(word_data.lesson_id)
        if not lesson:
            return self._format_error_response("Lesson not found")

        if not self._check_permissions(creator_id, [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       lesson.module.course.learning_center_id):
            return self._format_error_response("Insufficient permissions")

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

        if not self._check_permissions(creator_id, [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       lesson.module.course.learning_center_id):
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

    def update_word(self, word_id: int, update_data: WordUpdate, updater_id: int) -> Dict[str, Any]:
        """Update word"""
        word = self.repos.word.get(word_id)
        if not word:
            return self._format_error_response("Word not found")

        if not self._check_permissions(updater_id, [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       word.lesson.module.course.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        update_dict = update_data.dict(exclude_unset=True)
        updated_word = self.repos.word.update(word_id, update_dict)

        return self._format_success_response(
            WordResponse.from_orm(updated_word),
            "Word updated successfully"
        )

    def search_words(self, query: str, learning_center_id: int, requester_id: int) -> Dict[str, Any]:
        """Search words by foreign or native form"""
        if not self._check_permissions(requester_id,
                                       [UserRole.STUDENT, UserRole.TEACHER, UserRole.CONTENT_MANAGER, UserRole.ADMIN,
                                        UserRole.SUPER_ADMIN], learning_center_id):
            return self._format_error_response("Insufficient permissions")

        words = self.repos.word.search_words(learning_center_id, query)
        words_data = [WordResponse.from_orm(w) for w in words]

        return self._format_success_response(words_data)

    def get_random_words_for_quiz(self, lesson_id: int, count: int, requester_id: int) -> Dict[str, Any]:
        """Get random words from lesson for quiz generation"""
        lesson = self.repos.lesson.get(lesson_id)
        if not lesson:
            return self._format_error_response("Lesson not found")

        if not self._check_permissions(requester_id, [UserRole.STUDENT, UserRole.TEACHER],
                                       lesson.module.course.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        words = self.repos.word.get_random_words(lesson_id, count)
        words_data = [WordResponse.from_orm(w) for w in words]

        return self._format_success_response(words_data)

    def delete_word(self, word_id: int, deleter_id: int) -> Dict[str, Any]:
        """Delete word (soft delete by setting inactive)"""
        word = self.repos.word.get(word_id)
        if not word:
            return self._format_error_response("Word not found")

        if not self._check_permissions(deleter_id, [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       word.lesson.module.course.learning_center_id):
            return self._format_error_response("Insufficient permissions")

        # Soft delete by setting inactive
        updated_word = self.repos.word.update(word_id, {"is_active": False})

        return self._format_success_response(
            WordResponse.from_orm(updated_word),
            "Word deleted successfully"
        )

    def get_content_statistics(self, learning_center_id: int, requester_id: int) -> Dict[str, Any]:
        """Get content statistics for learning center"""
        if not self._check_permissions(requester_id, [UserRole.CONTENT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN],
                                       learning_center_id):
            return self._format_error_response("Insufficient permissions")

        courses = self.repos.course.get_by_center(learning_center_id)
        total_modules = 0
        total_lessons = 0
        total_words = 0

        for course in courses:
            total_modules += course.total_modules
            total_lessons += course.total_lessons
            total_words += course.total_words

        stats = {
            "total_courses": len(courses),
            "active_courses": len([c for c in courses if c.is_active]),
            "total_modules": total_modules,
            "total_lessons": total_lessons,
            "total_words": total_words
        }

        return self._format_success_response(stats)
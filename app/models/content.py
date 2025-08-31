from sqlalchemy import Column, String, Integer, ForeignKey, Text, Index, CheckConstraint

# SQLAlchemy naming convention to stabilize Alembic diffs
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

from sqlalchemy.orm import relationship
from .base import BaseModel


class Course(BaseModel):
    __tablename__ = "courses"

    # Basic info with validation
    name = Column(String(100), nullable=False)
    description = Column(Text)
    level = Column(String(20), nullable=False, default="beginner")
    order_index = Column(Integer, default=0, nullable=False)

    # Learning center relationship
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    learning_center = relationship("LearningCenter", back_populates="courses")

    # Relationships
    modules = relationship("Module", back_populates="course", cascade="all, delete-orphan",
                           order_by="Module.order_index")

    # Constraints
    __table_args__ = (
        CheckConstraint("level IN ('beginner', 'intermediate', 'advanced')", name='chk_valid_level'),
        CheckConstraint("length(name) >= 2", name='chk_name_length'),
        CheckConstraint("order_index >= 0", name='chk_order_positive'),
        Index('idx_course_center_active', 'learning_center_id', 'is_active'),
        Index('idx_course_center_order', 'learning_center_id', 'order_index'),
    )

    def __str__(self):
        return f"Course({self.name})"


class Module(BaseModel):
    __tablename__ = "modules"

    # Basic info with validation
    title = Column(String(100), nullable=False)
    description = Column(Text)
    order_index = Column(Integer, default=0, nullable=False)

    # Course relationship
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    course = relationship("Course", back_populates="modules")

    # Relationships
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan",
                           order_by="Lesson.order_index")

    # Constraints
    __table_args__ = (
        CheckConstraint("length(title) >= 2", name='chk_title_length'),
        CheckConstraint("order_index >= 0", name='chk_order_positive'),
        Index('idx_module_course_active', 'course_id', 'is_active'),
        Index('idx_module_course_order', 'course_id', 'order_index'),
    )

    def __str__(self):
        return f"Module({self.title})"


class Lesson(BaseModel):
    __tablename__ = "lessons"

    # Basic info with validation
    title = Column(String(100), nullable=False)
    description = Column(Text)
    content = Column(Text)  # Markdown content
    order_index = Column(Integer, default=0, nullable=False)

    # Module relationship
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    module = relationship("Module", back_populates="lessons")

    # Relationships
    words = relationship("Word", back_populates="lesson", cascade="all, delete-orphan",
                         order_by="Word.order_index")
    progress_records = relationship("Progress", back_populates="lesson", cascade="all, delete-orphan")
    quiz_sessions = relationship("QuizSession", back_populates="lesson", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint("length(title) >= 2", name='chk_title_length'),
        CheckConstraint("order_index >= 0", name='chk_order_positive'),
        Index('idx_lesson_module_active', 'module_id', 'is_active'),
        Index('idx_lesson_module_order', 'module_id', 'order_index'),
    )

    def __str__(self):
        return f"Lesson({self.title})"


class Word(BaseModel):
    __tablename__ = "words"

    # Word content with validation
    foreign_form = Column(String(100), nullable=False)
    native_form = Column(String(100), nullable=False)
    example_sentence = Column(Text)
    audio_url = Column(String(500))
    image_url = Column(String(500))
    order_index = Column(Integer, default=0, nullable=False)

    # Lesson relationship
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    lesson = relationship("Lesson", back_populates="words")

    # Relationships
    weak_words = relationship("WeakWord", back_populates="word", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint("length(foreign_form) >= 1", name='chk_foreign_length'),
        CheckConstraint("length(native_form) >= 1", name='chk_native_length'),
        CheckConstraint("order_index >= 0", name='chk_order_positive'),
        Index('idx_word_lesson_active', 'lesson_id', 'is_active'),
        Index('idx_word_lesson_order', 'lesson_id', 'order_index'),
    )

    def __str__(self):
        return f"Word({self.foreign_form} → {self.native_form})"
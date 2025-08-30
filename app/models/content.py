from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text, Index
from sqlalchemy.orm import relationship
from .base import BaseModel


class Course(BaseModel):
    __tablename__ = "courses"

    # Basic info
    name = Column(String(100), nullable=False)
    description = Column(Text)
    level = Column(String(20), nullable=False, default="beginner")  # beginner, intermediate, advanced
    is_active = Column(Boolean, default=True, nullable=False)
    order_index = Column(Integer, default=0)

    # Learning center
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    learning_center = relationship("LearningCenter", back_populates="courses")

    # Relationships
    modules = relationship("Module", back_populates="course", cascade="all, delete-orphan",
                           order_by="Module.order_index")

    # Indexes
    __table_args__ = (
        Index('idx_center_active', 'learning_center_id', 'is_active'),
        Index('idx_center_order', 'learning_center_id', 'order_index'),
    )

    def __str__(self):
        return f"Course({self.name}, {self.level})"

    @property
    def total_modules(self):
        return len([m for m in self.modules if m.is_active])

    @property
    def total_lessons(self):
        return sum(m.total_lessons for m in self.modules if m.is_active)

    @property
    def total_words(self):
        return sum(m.total_words for m in self.modules if m.is_active)


class Module(BaseModel):
    __tablename__ = "modules"

    # Basic info
    title = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    order_index = Column(Integer, default=0)

    # Course relationship
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    course = relationship("Course", back_populates="modules")

    # Relationships
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan",
                           order_by="Lesson.order_index")

    # Indexes
    __table_args__ = (
        Index('idx_course_active', 'course_id', 'is_active'),
        Index('idx_course_order', 'course_id', 'order_index'),
    )

    def __str__(self):
        return f"Module({self.title})"

    @property
    def total_lessons(self):
        return len([l for l in self.lessons if l.is_active])

    @property
    def total_words(self):
        return sum(l.total_words for l in self.lessons if l.is_active)


class Lesson(BaseModel):
    __tablename__ = "lessons"

    # Basic info
    title = Column(String(100), nullable=False)
    description = Column(Text)
    content = Column(Text)  # Markdown content for lesson explanations
    is_active = Column(Boolean, default=True, nullable=False)
    order_index = Column(Integer, default=0)

    # Module relationship
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    module = relationship("Module", back_populates="lessons")

    # Relationships
    words = relationship("Word", back_populates="lesson", cascade="all, delete-orphan",
                         order_by="Word.order_index")
    progress_records = relationship("Progress", back_populates="lesson", cascade="all, delete-orphan")
    quiz_sessions = relationship("QuizSession", back_populates="lesson", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_module_active', 'module_id', 'is_active'),
        Index('idx_module_order', 'module_id', 'order_index'),
    )

    def __str__(self):
        return f"Lesson({self.title})"

    @property
    def total_words(self):
        return len([w for w in self.words if w.is_active])

    @property
    def has_content(self):
        return bool(self.content and self.content.strip())


class Word(BaseModel):
    __tablename__ = "words"

    # Word content
    foreign_form = Column(String(100), nullable=False)  # English word
    native_form = Column(String(100), nullable=False)  # Uzbek translation
    example_sentence = Column(Text)
    audio_url = Column(String(255))
    image_url = Column(String(255))

    # Status and ordering
    is_active = Column(Boolean, default=True, nullable=False)
    order_index = Column(Integer, default=0)

    # Lesson relationship
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    lesson = relationship("Lesson", back_populates="words")

    # Relationships
    weak_words = relationship("WeakWord", back_populates="word", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_lesson_active', 'lesson_id', 'is_active'),
        Index('idx_lesson_order', 'lesson_id', 'order_index'),
        Index('idx_foreign_form', 'foreign_form'),
        Index('idx_native_form', 'native_form'),
    )

    def __str__(self):
        return f"Word({self.foreign_form} → {self.native_form})"

    @property
    def has_image(self):
        return bool(self.image_url)

    @property
    def has_audio(self):
        return bool(self.audio_url)
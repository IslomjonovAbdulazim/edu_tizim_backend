from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text
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

    def __str__(self):
        return f"Course({self.name}, {self.level})"


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

    def __str__(self):
        return f"Module({self.title})"


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

    def __str__(self):
        return f"Lesson({self.title})"

    @property
    def has_content(self):
        """Check if lesson has markdown content"""
        return bool(self.content and self.content.strip())


class Word(BaseModel):
    __tablename__ = "words"

    # Word content
    foreign_form = Column(String(100), nullable=False)  # English word
    native_form = Column(String(100), nullable=False)  # Uzbek translation
    example_sentence = Column(Text)
    audio_url = Column(String(255))

    # Simplified: single image URL instead of JSON array
    image_url = Column(String(255))

    # Status and ordering
    is_active = Column(Boolean, default=True, nullable=False)
    order_index = Column(Integer, default=0)

    # Lesson relationship
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    lesson = relationship("Lesson", back_populates="words")

    # Relationships
    weak_words = relationship("WeakWord", back_populates="word", cascade="all, delete-orphan")

    def __str__(self):
        return f"Word({self.foreign_form} → {self.native_form})"

    @property
    def has_image(self):
        """Check if word has an image"""
        return bool(self.image_url)
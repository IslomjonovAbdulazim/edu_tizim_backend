from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text, JSON
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

    @property
    def total_modules(self):
        return len(self.modules)

    @property
    def total_lessons(self):
        return sum(module.total_lessons for module in self.modules)

    @property
    def total_words(self):
        return sum(module.total_words for module in self.modules)


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

    @property
    def total_lessons(self):
        return len(self.lessons)

    @property
    def total_words(self):
        return sum(lesson.total_words for lesson in self.lessons)


class Lesson(BaseModel):
    __tablename__ = "lessons"

    # Basic info
    title = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    order_index = Column(Integer, default=0)

    # ADDED: Markdown content for lesson explanations
    content = Column(Text)  # Rich markdown text for lesson explanations, grammar rules, examples

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
    def total_words(self):
        return len(self.words)

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

    # ADDED: Multiple images for the word (up to 4)
    image_urls = Column(JSON)  # Array of image URLs: ["url1.jpg", "url2.jpg", "url3.jpg", "url4.jpg"]

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
    def has_images(self):
        """Check if word has any images"""
        return bool(self.image_urls and len(self.image_urls) > 0)

    @property
    def image_count(self):
        """Get number of images for this word"""
        return len(self.image_urls) if self.image_urls else 0

    def add_image(self, image_url: str):
        """Add an image URL to the word (max 4)"""
        if not self.image_urls:
            self.image_urls = []

        if len(self.image_urls) < 4 and image_url not in self.image_urls:
            self.image_urls = self.image_urls + [image_url]  # Create new list for SQLAlchemy to detect change
            return True
        return False

    def remove_image(self, image_url: str):
        """Remove an image URL from the word"""
        if self.image_urls and image_url in self.image_urls:
            new_images = [img for img in self.image_urls if img != image_url]
            self.image_urls = new_images if new_images else None
            return True
        return False

    def get_images(self):
        """Get all image URLs as a list"""
        return self.image_urls if self.image_urls else []

    def get_primary_image(self):
        """Get the first (primary) image URL"""
        return self.image_urls[0] if self.image_urls and len(self.image_urls) > 0 else None

    def reorder_images(self, new_order: list):
        """Reorder images based on provided list of URLs"""
        if not self.image_urls or not new_order:
            return False

        # Validate that all URLs in new_order exist in current images
        if all(url in self.image_urls for url in new_order) and len(new_order) == len(self.image_urls):
            self.image_urls = new_order
            return True
        return False
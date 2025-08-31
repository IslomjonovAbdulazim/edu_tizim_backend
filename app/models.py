from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
import sqlalchemy as sa

Base = declarative_base()


class UserRole(PyEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), unique=True, index=True, nullable=True)
    email = Column(String(100), unique=True, index=True, nullable=True)
    password_hash = Column(String(200), nullable=True)
    telegram_id = Column(String(50), nullable=True)
    avatar = Column(String(200), nullable=True)
    role = Column(sa.Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    profiles = relationship("LearningCenterProfile", back_populates="user")
    owned_centers = relationship("LearningCenter", back_populates="owner")


class LearningCenter(Base):
    __tablename__ = "learning_centers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    logo = Column(String(300), nullable=True)
    days_remaining = Column(Integer, default=0)
    student_limit = Column(Integer, default=50)
    is_active = Column(Boolean, default=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    owner = relationship("User", back_populates="owned_centers")
    profiles = relationship("LearningCenterProfile", back_populates="center")
    groups = relationship("Group", back_populates="center")
    courses = relationship("Course", back_populates="center")
    payments = relationship("Payment", back_populates="center")


class LearningCenterProfile(Base):
    __tablename__ = "learning_center_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    center_id = Column(Integer, ForeignKey("learning_centers.id"))
    full_name = Column(String(200), nullable=False)
    role_in_center = Column(sa.Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="profiles")
    center = relationship("LearningCenter", back_populates="profiles")
    group_memberships = relationship("GroupMember", back_populates="profile")
    progress = relationship("Progress", back_populates="profile")
    coins = relationship("Coin", back_populates="profile")


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    center_id = Column(Integer, ForeignKey("learning_centers.id"))
    teacher_id = Column(Integer, ForeignKey("learning_center_profiles.id"), nullable=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    center = relationship("LearningCenter", back_populates="groups")
    members = relationship("GroupMember", back_populates="group")
    course = relationship("Course", back_populates="groups")


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    profile_id = Column(Integer, ForeignKey("learning_center_profiles.id"))
    joined_at = Column(DateTime, server_default=func.now())

    # Relationships
    group = relationship("Group", back_populates="members")
    profile = relationship("LearningCenterProfile", back_populates="group_memberships")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    center_id = Column(Integer, ForeignKey("learning_centers.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    center = relationship("LearningCenter", back_populates="courses")
    modules = relationship("Module", back_populates="course")
    groups = relationship("Group", back_populates="course")


class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    course = relationship("Course", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module")


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    module_id = Column(Integer, ForeignKey("modules.id"))
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    module = relationship("Module", back_populates="lessons")
    words = relationship("Word", back_populates="lesson")
    progress = relationship("Progress", back_populates="lesson")


class Word(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(200), nullable=False)
    meaning = Column(String(500), nullable=False)
    definition = Column(Text, nullable=True)
    example_sentence = Column(Text, nullable=True)
    image_url = Column(String(300), nullable=True)
    audio_url = Column(String(300), nullable=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    lesson = relationship("Lesson", back_populates="words")
    progress = relationship("WordProgress", back_populates="word")


class Progress(Base):
    __tablename__ = "progress"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("learning_center_profiles.id"))
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    percentage = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    last_practiced = Column(DateTime, server_default=func.now())

    # Relationships
    profile = relationship("LearningCenterProfile", back_populates="progress")
    lesson = relationship("Lesson", back_populates="progress")


class WordProgress(Base):
    __tablename__ = "word_progress"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("learning_center_profiles.id"))
    word_id = Column(Integer, ForeignKey("words.id"))
    last_seven_attempts = Column(String(7), default="")  # "1010110" format
    total_correct = Column(Integer, default=0)
    total_attempts = Column(Integer, default=0)
    last_practiced = Column(DateTime, server_default=func.now())

    # Relationships
    word = relationship("Word", back_populates="progress")


class Coin(Base):
    __tablename__ = "coins"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("learning_center_profiles.id"))
    amount = Column(Integer, default=1)
    source = Column(String(50))  # "lesson", "revision", "bonus"
    source_id = Column(Integer, nullable=True)  # lesson_id or other reference
    earned_at = Column(DateTime, server_default=func.now())

    # Relationships
    profile = relationship("LearningCenterProfile", back_populates="coins")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    center_id = Column(Integer, ForeignKey("learning_centers.id"))
    amount = Column(Float, nullable=False)
    days_added = Column(Integer, nullable=False)
    description = Column(String(300), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))  # super admin
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    center = relationship("LearningCenter", back_populates="payments")
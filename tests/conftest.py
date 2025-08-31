import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Now we can import from app
from app.main import app
from app.database import get_db, Base
from app.models import *

# Load environment variables
load_dotenv()

# Test database setup - use actual database from .env
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost/test_db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def setup_database():
    """Set up test database"""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop all tables after tests
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client():
    """Create test client with database override"""
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sample_center():
    """Create a sample learning center for tests"""
    db = TestingSessionLocal()
    
    center = LearningCenter(
        title="Sample Center",
        student_limit=100,
        owner_id=1,
        days_remaining=30,
        is_active=True
    )
    db.add(center)
    db.commit()
    db.refresh(center)
    
    yield center
    
    db.close()


@pytest.fixture
def sample_admin_user():
    """Create a sample admin user for tests"""
    from app.utils import hash_password
    
    db = TestingSessionLocal()
    
    admin_user = User(
        email="admin@test.com",
        password_hash=hash_password("password123"),
        role=UserRole.ADMIN,
        is_active=True
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    yield admin_user
    
    db.close()


@pytest.fixture
def sample_teacher_user():
    """Create a sample teacher user for tests"""
    from app.utils import hash_password
    
    db = TestingSessionLocal()
    
    teacher_user = User(
        email="teacher@test.com",
        password_hash=hash_password("teacher123"),
        role=UserRole.TEACHER,
        is_active=True
    )
    db.add(teacher_user)
    db.commit()
    db.refresh(teacher_user)
    
    yield teacher_user
    
    db.close()


@pytest.fixture
def sample_student_user():
    """Create a sample student user for tests"""
    db = TestingSessionLocal()
    
    student_user = User(
        phone="+998901234567",
        telegram_id="123456789",
        role=UserRole.STUDENT,
        is_active=True
    )
    db.add(student_user)
    db.commit()
    db.refresh(student_user)
    
    yield student_user
    
    db.close()


@pytest.fixture
def sample_super_admin_user():
    """Create a sample super admin user for tests"""
    from app.utils import hash_password
    
    db = TestingSessionLocal()
    
    super_admin_user = User(
        email="superadmin@test.com",
        password_hash=hash_password("superpass123"),
        role=UserRole.SUPER_ADMIN,
        is_active=True
    )
    db.add(super_admin_user)
    db.commit()
    db.refresh(super_admin_user)
    
    yield super_admin_user
    
    db.close()


@pytest.fixture
def sample_course_structure():
    """Create a complete course structure for tests"""
    db = TestingSessionLocal()
    
    # Create center
    center = LearningCenter(
        title="Test Center",
        student_limit=100,
        owner_id=1,
        days_remaining=30,
        is_active=True
    )
    db.add(center)
    db.commit()
    
    # Create course
    course = Course(
        title="Test Course",
        description="A comprehensive test course",
        center_id=center.id,
        is_active=True
    )
    db.add(course)
    db.commit()
    
    # Create module
    module = Module(
        title="Test Module",
        description="A test module",
        course_id=course.id,
        order_index=1,
        is_active=True
    )
    db.add(module)
    db.commit()
    
    # Create lesson
    lesson = Lesson(
        title="Test Lesson",
        description="A test lesson",
        module_id=module.id,
        order_index=1,
        is_active=True
    )
    db.add(lesson)
    db.commit()
    
    # Create words
    words = []
    word_data = [
        ("hello", "salom", "A greeting", "Hello, how are you?"),
        ("goodbye", "xayr", "A farewell", "Goodbye, see you later!"),
        ("thank you", "rahmat", "Expression of gratitude", "Thank you very much!")
    ]
    
    for i, (word, meaning, definition, example) in enumerate(word_data):
        word_obj = Word(
            word=word,
            meaning=meaning,
            definition=definition,
            example_sentence=example,
            lesson_id=lesson.id,
            order_index=i + 1,
            is_active=True
        )
        words.append(word_obj)
        db.add(word_obj)
    
    db.commit()
    
    structure = {
        "center": center,
        "course": course,
        "module": module,
        "lesson": lesson,
        "words": words
    }
    
    yield structure
    
    db.close()


@pytest.fixture
def auth_tokens():
    """Create authentication tokens for different user roles"""
    from app.utils import create_access_token
    
    tokens = {
        "admin": create_access_token({
            "user_id": 1,
            "center_id": 1,
            "role": "admin"
        }),
        "teacher": create_access_token({
            "user_id": 2,
            "center_id": 1,
            "role": "teacher"
        }),
        "student": create_access_token({
            "user_id": 3,
            "center_id": 1,
            "role": "student"
        }),
        "super_admin": create_access_token({
            "user_id": 4,
            "center_id": None,
            "role": "super_admin"
        })
    }
    
    return tokens


@pytest.fixture
def mock_redis():
    """Mock Redis service for testing"""
    with patch('app.database.redis_client') as mock_redis_client:
        mock_redis_client.ping.return_value = True
        mock_redis_client.get.return_value = None
        mock_redis_client.set.return_value = True
        mock_redis_client.delete.return_value = True
        mock_redis_client.exists.return_value = False
        yield mock_redis_client


@pytest.fixture
def mock_telegram():
    """Mock Telegram service for testing"""
    with patch('app.utils.send_telegram_message') as mock_send:
        mock_send.return_value = True
        yield mock_send


# Environment setup for tests
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables"""
    os.environ["TESTING"] = "1"
    yield
    # Clean up
    if "TESTING" in os.environ:
        del os.environ["TESTING"]


# Mock services for testing
@pytest.fixture
def mock_content_service():
    """Mock ContentService for testing"""
    with patch('app.services.ContentService') as mock_service:
        mock_service.get_course_content.return_value = []
        mock_service.get_lesson_words.return_value = []
        mock_service.invalidate_center_cache.return_value = None
        yield mock_service


@pytest.fixture
def mock_progress_service():
    """Mock ProgressService for testing"""
    with patch('app.services.ProgressService') as mock_service:
        mock_service.update_lesson_progress.return_value = None
        mock_service.update_word_progress.return_value = None
        mock_service.get_weak_words.return_value = []
        yield mock_service


@pytest.fixture
def mock_leaderboard_service():
    """Mock LeaderboardService for testing"""
    with patch('app.services.LeaderboardService') as mock_service:
        mock_service.get_center_leaderboard.return_value = []
        mock_service.get_group_leaderboard.return_value = []
        yield mock_service


@pytest.fixture
def mock_payment_service():
    """Mock PaymentService for testing"""
    with patch('app.services.PaymentService') as mock_service:
        mock_service.add_payment.return_value = Payment(
            id=1,
            center_id=1,
            amount=100.0,
            days_added=30,
            description="Test payment"
        )
        yield mock_service


# Utility functions for tests
def create_test_token(user_id: int, center_id: int = None, role: str = "student"):
    """Helper function to create test JWT tokens"""
    from app.utils import create_access_token
    
    return create_access_token({
        "user_id": user_id,
        "center_id": center_id,
        "role": role
    })


def get_auth_headers(token: str):
    """Helper function to create authorization headers"""
    return {"Authorization": f"Bearer {token}"}


# Test data constants
TEST_PHONE_NUMBERS = [
    "+998901234567",
    "+998902345678", 
    "+998903456789",
    "+998904567890",
    "+998905678901"
]

TEST_EMAILS = [
    "admin1@test.com",
    "admin2@test.com",
    "teacher1@test.com", 
    "teacher2@test.com",
    "superadmin@test.com"
]

TEST_TELEGRAM_IDS = [
    "123456789",
    "234567890",
    "345678901",
    "456789012",
    "567890123"
]


# Test data factories
class TestDataFactory:
    """Factory class for creating test data"""
    
    @staticmethod
    def create_learning_center(db: Session, **kwargs):
        """Create a test learning center"""
        defaults = {
            "title": "Test Center",
            "student_limit": 100,
            "owner_id": 1,
            "days_remaining": 30,
            "is_active": True
        }
        defaults.update(kwargs)
        
        center = LearningCenter(**defaults)
        db.add(center)
        db.commit()
        db.refresh(center)
        return center
    
    @staticmethod
    def create_user(db: Session, role: UserRole, **kwargs):
        """Create a test user"""
        from app.utils import hash_password
        
        defaults = {
            "is_active": True,
            "role": role
        }
        
        if role in [UserRole.ADMIN, UserRole.TEACHER, UserRole.SUPER_ADMIN]:
            defaults.update({
                "email": f"{role.value}@test.com",
                "password_hash": hash_password("password123")
            })
        else:  # STUDENT
            defaults.update({
                "phone": "+998901234567",
                "telegram_id": "123456789"
            })
        
        defaults.update(kwargs)
        
        user = User(**defaults)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def create_profile(db: Session, user_id: int, center_id: int, role: UserRole, **kwargs):
        """Create a learning center profile"""
        defaults = {
            "user_id": user_id,
            "center_id": center_id,
            "full_name": f"Test {role.value.title()}",
            "role_in_center": role,
            "is_active": True
        }
        defaults.update(kwargs)
        
        profile = LearningCenterProfile(**defaults)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile
    
    @staticmethod
    def create_course_structure(db: Session, center_id: int):
        """Create a complete course structure"""
        # Create course
        course = Course(
            title="Test Course",
            description="A test course",
            center_id=center_id,
            is_active=True
        )
        db.add(course)
        db.commit()
        
        # Create module
        module = Module(
            title="Test Module",
            description="A test module",
            course_id=course.id,
            order_index=1,
            is_active=True
        )
        db.add(module)
        db.commit()
        
        # Create lesson
        lesson = Lesson(
            title="Test Lesson",
            description="A test lesson",
            module_id=module.id,
            order_index=1,
            is_active=True
        )
        db.add(lesson)
        db.commit()
        
        # Create words
        words = []
        word_data = [
            ("hello", "salom", "A greeting", "Hello, how are you?"),
            ("goodbye", "xayr", "A farewell", "Goodbye, see you later!"),
            ("thank you", "rahmat", "Expression of gratitude", "Thank you!")
        ]
        
        for i, (word, meaning, definition, example) in enumerate(word_data):
            word_obj = Word(
                word=word,
                meaning=meaning,
                definition=definition,
                example_sentence=example,
                lesson_id=lesson.id,
                order_index=i + 1,
                is_active=True
            )
            words.append(word_obj)
            db.add(word_obj)
        
        db.commit()
        
        return {
            "course": course,
            "module": module,
            "lesson": lesson,
            "words": words
        }
    
    @staticmethod
    def create_group_with_members(db: Session, teacher_id: int, course_id: int, center_id: int, student_count: int = 3):
        """Create a group with students"""
        group = Group(
            name="Test Group",
            center_id=center_id,
            teacher_id=teacher_id,
            course_id=course_id,
            is_active=True
        )
        db.add(group)
        db.commit()
        
        # Create students and add to group
        students = []
        for i in range(student_count):
            student_user = TestDataFactory.create_user(
                db, 
                UserRole.STUDENT,
                phone=f"+99890123456{i}",
                telegram_id=f"12345678{i}"
            )
            
            student_profile = TestDataFactory.create_profile(
                db,
                student_user.id,
                center_id,
                UserRole.STUDENT,
                full_name=f"Test Student {i}"
            )
            
            # Add to group
            member = GroupMember(
                group_id=group.id,
                profile_id=student_profile.id
            )
            db.add(member)
            students.append(student_profile)
        
        db.commit()
        
        return group, students


# Environment setup for tests
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables"""
    os.environ["TESTING"] = "1"
    yield
    # Clean up
    if "TESTING" in os.environ:
        del os.environ["TESTING"]


# Mock services for testing
@pytest.fixture
def mock_content_service():
    """Mock ContentService for testing"""
    with patch('app.services.ContentService') as mock_service:
        mock_service.get_course_content.return_value = []
        mock_service.get_lesson_words.return_value = []
        mock_service.invalidate_center_cache.return_value = None
        yield mock_service


@pytest.fixture
def mock_progress_service():
    """Mock ProgressService for testing"""
    with patch('app.services.ProgressService') as mock_service:
        mock_service.update_lesson_progress.return_value = None
        mock_service.update_word_progress.return_value = None
        mock_service.get_weak_words.return_value = []
        yield mock_service


@pytest.fixture
def mock_leaderboard_service():
    """Mock LeaderboardService for testing"""
    with patch('app.services.LeaderboardService') as mock_service:
        mock_service.get_center_leaderboard.return_value = []
        mock_service.get_group_leaderboard.return_value = []
        yield mock_service


@pytest.fixture
def mock_payment_service():
    """Mock PaymentService for testing"""
    with patch('app.services.PaymentService') as mock_service:
        mock_service.add_payment.return_value = Payment(
            id=1,
            center_id=1,
            amount=100.0,
            days_added=30,
            description="Test payment"
        )
        yield mock_service


# Utility functions for tests
def create_test_token(user_id: int, center_id: int = None, role: str = "student"):
    """Helper function to create test JWT tokens"""
    from app.utils import create_access_token
    
    return create_access_token({
        "user_id": user_id,
        "center_id": center_id,
        "role": role
    })


def get_auth_headers(token: str):
    """Helper function to create authorization headers"""
    return {"Authorization": f"Bearer {token}"}


# Custom assertions for testing
class TestAssertions:
    """Custom assertion helpers for testing"""
    
    @staticmethod
    def assert_api_response_success(response, expected_keys=None):
        """Assert successful API response format"""
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        
        if expected_keys:
            for key in expected_keys:
                assert key in data.get("data", {})
    
    @staticmethod
    def assert_api_response_error(response, expected_status_code, expected_message=None):
        """Assert error API response format"""
        assert response.status_code == expected_status_code
        data = response.json()
        
        if expected_message:
            assert expected_message in data.get("detail", "")
    
    @staticmethod
    def assert_paginated_response(response, expected_total=None):
        """Assert paginated response format"""
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        
        if expected_total is not None:
            assert data["total"] == expected_total


# Database cleanup utilities
@pytest.fixture
def clean_database():
    """Clean database before and after test"""
    db = TestingSessionLocal()
    
    # Clean before test
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    
    yield db
    
    # Clean after test
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()


# Performance testing utilities
@pytest.fixture
def performance_monitor():
    """Monitor test performance"""
    import time
    
    start_time = time.time()
    yield
    end_time = time.time()
    
    execution_time = end_time - start_time
    # Log slow tests (over 2 seconds)
    if execution_time > 2.0:
        print(f"⚠️ Slow test detected: {execution_time:.2f}s")


# Error simulation fixtures
@pytest.fixture
def simulate_database_error():
    """Simulate database connection errors"""
    with patch('app.database.SessionLocal') as mock_session:
        mock_session.side_effect = Exception("Database connection failed")
        yield mock_session


@pytest.fixture
def simulate_redis_error():
    """Simulate Redis connection errors"""
    with patch('app.database.redis_client') as mock_redis:
        mock_redis.ping.side_effect = Exception("Redis connection failed")
        mock_redis.get.side_effect = Exception("Redis error")
        mock_redis.set.side_effect = Exception("Redis error")
        yield mock_redis
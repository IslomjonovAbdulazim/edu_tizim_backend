from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from ..database import get_db
from ..models import *
from ..services import ContentService, LeaderboardService
from ..utils import APIResponse, get_current_user_data, check_center_active, hash_password, paginate, format_phone
from .. import schemas

router = APIRouter()


def get_admin_user(current_user: dict = Depends(get_current_user_data)):
    """Require admin role"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    if not current_user["center_id"]:
        raise HTTPException(status_code=403, detail="No center access")
    return current_user


@router.get("/dashboard")
def admin_dashboard(
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Admin dashboard with key metrics"""
    center_id = current_user["center_id"]
    check_center_active(center_id, db)

    # Get stats
    total_students = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.center_id == center_id,
        LearningCenterProfile.role_in_center == UserRole.STUDENT,
        LearningCenterProfile.is_active == True
    ).count()

    total_teachers = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.center_id == center_id,
        LearningCenterProfile.role_in_center == UserRole.TEACHER,
        LearningCenterProfile.is_active == True
    ).count()

    total_groups = db.query(Group).filter(
        Group.center_id == center_id,
        Group.is_active == True
    ).count()

    total_courses = db.query(Course).filter(
        Course.center_id == center_id,
        Course.is_active == True
    ).count()

    # Recent students
    recent_students = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.center_id == center_id,
        LearningCenterProfile.role_in_center == UserRole.STUDENT
    ).order_by(desc(LearningCenterProfile.created_at)).limit(5).all()

    return APIResponse.success({
        "stats": {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_groups": total_groups,
            "total_courses": total_courses
        },
        "recent_students": [{
            "id": s.id,
            "full_name": s.full_name,
            "created_at": s.created_at
        } for s in recent_students],
        "center": {
            "title": current_user["center"].title,
            "days_remaining": current_user["center"].days_remaining,
            "student_limit": current_user["center"].student_limit
        }
    })


# User Management
@router.post("/users/students")
def create_student(
        student_data: schemas.StudentCreate,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Create new student account"""
    center_id = current_user["center_id"]
    check_center_active(center_id, db)

    phone = format_phone(student_data.phone)

    # Check if user exists
    existing_user = db.query(User).filter(User.phone == phone).first()

    if not existing_user:
        user = User(
            phone=phone,
            telegram_id=student_data.telegram_id,
            role=UserRole.STUDENT,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user = existing_user

    # Check if profile already exists in this center
    existing_profile = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.user_id == user.id,
        LearningCenterProfile.center_id == center_id
    ).first()

    if existing_profile:
        raise HTTPException(status_code=400, detail="Student already exists in this center")

    profile = LearningCenterProfile(
        user_id=user.id,
        center_id=center_id,
        full_name=student_data.full_name,
        role_in_center=UserRole.STUDENT,
        is_active=True
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return APIResponse.success({
        "profile_id": profile.id,
        "message": "Student created successfully"
    })


@router.post("/users/teachers")
def create_teacher(
        teacher_data: schemas.TeacherCreate,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Create new teacher account"""
    center_id = current_user["center_id"]
    check_center_active(center_id, db)

    # Check if user exists
    existing_user = db.query(User).filter(User.email == teacher_data.email).first()

    if not existing_user:
        user = User(
            email=teacher_data.email,
            password_hash=hash_password(teacher_data.password),
            role=UserRole.TEACHER,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user = existing_user

    # Check if profile already exists
    existing_profile = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.user_id == user.id,
        LearningCenterProfile.center_id == center_id
    ).first()

    if existing_profile:
        raise HTTPException(status_code=400, detail="Teacher already exists in this center")

    profile = LearningCenterProfile(
        user_id=user.id,
        center_id=center_id,
        full_name=teacher_data.full_name,
        role_in_center=UserRole.TEACHER,
        is_active=True
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return APIResponse.success({
        "profile_id": profile.id,
        "message": "Teacher created successfully"
    })


@router.get("/users/students")
def get_students(
        page: int = 1,
        size: int = 20,
        search: str = None,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Get all students in center"""
    center_id = current_user["center_id"]

    query = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.center_id == center_id,
        LearningCenterProfile.role_in_center == UserRole.STUDENT,
        LearningCenterProfile.is_active == True
    )

    if search:
        query = query.filter(LearningCenterProfile.full_name.ilike(f"%{search}%"))

    result = paginate(query, page, size)
    return APIResponse.paginated(result["items"], result["total"], result["page"], result["size"])


@router.get("/users/teachers")
def get_teachers(
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Get all teachers in center"""
    center_id = current_user["center_id"]

    teachers = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.center_id == center_id,
        LearningCenterProfile.role_in_center == UserRole.TEACHER,
        LearningCenterProfile.is_active == True
    ).all()

    return APIResponse.success([{
        "id": t.id,
        "full_name": t.full_name,
        "created_at": t.created_at
    } for t in teachers])


# Group Management
@router.post("/groups")
def create_group(
        group_data: schemas.GroupCreate,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Create new group"""
    center_id = current_user["center_id"]
    check_center_active(center_id, db)

    group = Group(
        name=group_data.name,
        center_id=center_id,
        teacher_id=group_data.teacher_id,
        course_id=group_data.course_id,
        is_active=True
    )
    db.add(group)
    db.commit()
    db.refresh(group)

    return APIResponse.success({"group_id": group.id, "message": "Group created successfully"})


@router.get("/groups")
def get_groups(
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Get all groups in center"""
    center_id = current_user["center_id"]

    groups = db.query(Group).filter(
        Group.center_id == center_id,
        Group.is_active == True
    ).all()

    return APIResponse.success([{
        "id": g.id,
        "name": g.name,
        "teacher_id": g.teacher_id,
        "course_id": g.course_id,
        "created_at": g.created_at
    } for g in groups])


@router.post("/groups/{group_id}/members")
def add_group_members(
        group_id: int,
        member_data: schemas.GroupMemberAdd,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Add students to group"""
    # Verify group belongs to center
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.center_id == current_user["center_id"]
    ).first()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    added = 0
    for profile_id in member_data.profile_ids:
        # Verify profile belongs to center
        profile = db.query(LearningCenterProfile).filter(
            LearningCenterProfile.id == profile_id,
            LearningCenterProfile.center_id == current_user["center_id"]
        ).first()

        if not profile:
            continue

        # Check if already member
        existing = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.profile_id == profile_id
        ).first()

        if not existing:
            member = GroupMember(
                group_id=group_id,
                profile_id=profile_id
            )
            db.add(member)
            added += 1

    db.commit()
    return APIResponse.success({"message": f"Added {added} members to group"})


# Course Management
@router.post("/courses")
def create_course(
        course_data: schemas.CourseCreate,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Create new course"""
    center_id = current_user["center_id"]
    check_center_active(center_id, db)

    course = Course(
        title=course_data.title,
        description=course_data.description,
        center_id=center_id,
        is_active=True
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    # Clear cache
    ContentService.invalidate_center_cache(center_id)

    return APIResponse.success({"course_id": course.id, "message": "Course created successfully"})


@router.post("/courses/{course_id}/modules")
def create_module(
        course_id: int,
        module_data: schemas.ModuleCreate,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Create new module in course"""
    # Verify course belongs to center
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.center_id == current_user["center_id"]
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    module = Module(
        title=module_data.title,
        description=module_data.description,
        course_id=course_id,
        order_index=module_data.order_index,
        is_active=True
    )
    db.add(module)
    db.commit()
    db.refresh(module)

    # Clear cache
    ContentService.invalidate_center_cache(current_user["center_id"])

    return APIResponse.success({"module_id": module.id, "message": "Module created successfully"})


@router.post("/modules/{module_id}/lessons")
def create_lesson(
        module_id: int,
        lesson_data: schemas.LessonCreate,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Create new lesson in module"""
    # Verify module belongs to center
    module = db.query(Module).join(Course).filter(
        Module.id == module_id,
        Course.center_id == current_user["center_id"]
    ).first()

    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    lesson = Lesson(
        title=lesson_data.title,
        description=lesson_data.description,
        module_id=module_id,
        order_index=lesson_data.order_index,
        is_active=True
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)

    # Clear cache
    ContentService.invalidate_center_cache(current_user["center_id"])

    return APIResponse.success({"lesson_id": lesson.id, "message": "Lesson created successfully"})


@router.post("/lessons/{lesson_id}/words")
def create_word(
        lesson_id: int,
        word_data: schemas.WordCreate,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Add word to lesson"""
    # Verify lesson belongs to center
    lesson = db.query(Lesson).join(Module).join(Course).filter(
        Lesson.id == lesson_id,
        Course.center_id == current_user["center_id"]
    ).first()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    word = Word(
        word=word_data.word,
        meaning=word_data.meaning,
        definition=word_data.definition,
        example_sentence=word_data.example_sentence,
        image_url=word_data.image_url,
        audio_url=word_data.audio_url,
        lesson_id=lesson_id,
        order_index=word_data.order_index,
        is_active=True
    )
    db.add(word)
    db.commit()
    db.refresh(word)

    # Clear cache
    ContentService.invalidate_center_cache(current_user["center_id"])

    return APIResponse.success({"word_id": word.id, "message": "Word added successfully"})


@router.post("/lessons/{lesson_id}/words/bulk")
def create_bulk_words(
        lesson_id: int,
        bulk_data: schemas.BulkWordCreate,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Add multiple words to lesson"""
    # Verify lesson belongs to center
    lesson = db.query(Lesson).join(Module).join(Course).filter(
        Lesson.id == lesson_id,
        Course.center_id == current_user["center_id"]
    ).first()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    words = []
    for i, word_data in enumerate(bulk_data.words):
        word = Word(
            word=word_data.word,
            meaning=word_data.meaning,
            definition=word_data.definition,
            example_sentence=word_data.example_sentence,
            image_url=word_data.image_url,
            audio_url=word_data.audio_url,
            lesson_id=lesson_id,
            order_index=word_data.order_index or i,
            is_active=True
        )
        words.append(word)

    db.add_all(words)
    db.commit()

    # Clear cache
    ContentService.invalidate_center_cache(current_user["center_id"])

    return APIResponse.success({"message": f"Added {len(words)} words successfully"})


# Analytics
@router.get("/analytics/overview")
def get_analytics_overview(
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Get learning center analytics"""
    center_id = current_user["center_id"]

    # Get top students
    top_students = LeaderboardService.get_center_leaderboard(db, center_id, 10)

    # Total lessons and completion
    total_lessons = db.query(Lesson).join(Module).join(Course).filter(
        Course.center_id == center_id,
        Course.is_active == True,
        Module.is_active == True,
        Lesson.is_active == True
    ).count()

    completed_lessons = db.query(Progress).join(LearningCenterProfile).filter(
        LearningCenterProfile.center_id == center_id,
        Progress.completed == True
    ).count()

    return APIResponse.success({
        "total_lessons": total_lessons,
        "completed_lessons": completed_lessons,
        "completion_rate": round((completed_lessons / max(total_lessons, 1)) * 100, 2),
        "top_students": top_students
    })
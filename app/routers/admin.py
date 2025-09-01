from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from ..database import get_db
from ..models import *
from ..services import ContentService, LeaderboardService
from ..utils import APIResponse, get_current_user_data, check_center_active, hash_password, paginate, format_phone, validate_uzbek_phone
from ..dependencies import get_current_user
from .. import schemas
import os
import uuid
from pathlib import Path

router = APIRouter()


def get_admin_user(current_user: dict = Depends(get_current_user)):
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
    
    # Validate Uzbekistan phone number
    if not validate_uzbek_phone(phone):
        raise HTTPException(status_code=400, detail="Invalid Uzbekistan phone number format")

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

    query = db.query(LearningCenterProfile).join(User).filter(
        LearningCenterProfile.center_id == center_id,
        LearningCenterProfile.role_in_center == UserRole.STUDENT,
        LearningCenterProfile.is_active == True
    )

    if search:
        query = query.filter(LearningCenterProfile.full_name.ilike(f"%{search}%"))

    result = paginate(query, page, size)
    
    # Add phone from User table to each student
    students_with_phone = []
    for student in result["items"]:
        user = db.query(User).filter(User.id == student.user_id).first()
        student_dict = {
            "id": student.id,
            "user_id": student.user_id,
            "center_id": student.center_id,
            "full_name": student.full_name,
            "phone": user.phone if user else None,
            "role_in_center": student.role_in_center,
            "is_active": student.is_active,
            "created_at": student.created_at,
            "updated_at": student.updated_at
        }
        students_with_phone.append(student_dict)
    
    return APIResponse.paginated(students_with_phone, result["total"], result["page"], result["size"])


@router.get("/users/teachers")
def get_teachers(
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Get all teachers in center"""
    center_id = current_user["center_id"]

    teachers = db.query(LearningCenterProfile).join(User).filter(
        LearningCenterProfile.center_id == center_id,
        LearningCenterProfile.role_in_center == UserRole.TEACHER,
        LearningCenterProfile.is_active == True
    ).all()

    teachers_with_email = []
    for teacher in teachers:
        user = db.query(User).filter(User.id == teacher.user_id).first()
        teachers_with_email.append({
            "id": teacher.id,
            "full_name": teacher.full_name,
            "email": user.email if user else None,
            "created_at": teacher.created_at
        })

    return APIResponse.success(teachers_with_email)


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


@router.get("/groups/{group_id}/members")
def get_group_members(
        group_id: int,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Get all members in group"""
    # Verify group belongs to center
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.center_id == current_user["center_id"]
    ).first()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Get all group members with profile information
    members = db.query(GroupMember).join(LearningCenterProfile).filter(
        GroupMember.group_id == group_id,
        LearningCenterProfile.is_active == True
    ).all()

    return APIResponse.success([{
        "profile_id": member.profile_id,
        "full_name": member.profile.full_name,
        "joined_at": member.created_at
    } for member in members])


@router.post("/groups/{group_id}/members/{profile_id}")
def add_individual_student_to_group(
        group_id: int,
        profile_id: int,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Add individual student to group"""
    # Verify group belongs to center
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.center_id == current_user["center_id"]
    ).first()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Verify profile belongs to center
    profile = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.id == profile_id,
        LearningCenterProfile.center_id == current_user["center_id"],
        LearningCenterProfile.role_in_center == UserRole.STUDENT
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Student not found")

    # Check if already member
    existing = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.profile_id == profile_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Student already in group")

    member = GroupMember(
        group_id=group_id,
        profile_id=profile_id
    )
    db.add(member)
    db.commit()

    return APIResponse.success({"message": "Student added to group successfully"})


@router.put("/groups/{group_id}")
def update_group(
        group_id: int,
        group_data: schemas.GroupUpdate,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Update group information"""
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.center_id == current_user["center_id"]
    ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    group.name = group_data.name
    group.teacher_id = group_data.teacher_id
    group.course_id = group_data.course_id
    db.commit()
    
    return APIResponse.success({"message": "Group updated successfully"})


@router.delete("/groups/{group_id}")
def delete_group(
        group_id: int,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Soft delete group"""
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.center_id == current_user["center_id"]
    ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    group.is_active = False
    db.commit()
    
    return APIResponse.success({"message": "Group deleted successfully"})


@router.delete("/groups/{group_id}/members/{profile_id}")
def remove_student_from_group(
        group_id: int,
        profile_id: int,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Remove student from group"""
    # Verify group belongs to center
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.center_id == current_user["center_id"]
    ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Remove member
    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.profile_id == profile_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Student not in group")
    
    db.delete(member)
    db.commit()
    
    return APIResponse.success({"message": "Student removed from group successfully"})


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


# File Upload Utilities
def save_uploaded_file(file: UploadFile, folder: str) -> str:
    """Save uploaded file and return relative path"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    try:
        # Use persistent storage path from environment
        base_storage = os.getenv("STORAGE_PATH", "/tmp/persistent_storage")
        storage_path = Path(base_storage) / folder
        storage_path.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix.lower()
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = storage_path / unique_filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)
        
        return f"/storage/{folder}/{unique_filename}"
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")


# Student Management CRUD
@router.put("/users/students/{profile_id}")
def update_student(
        profile_id: int,
        student_data: schemas.StudentUpdate,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Update student information"""
    center_id = current_user["center_id"]
    
    profile = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.id == profile_id,
        LearningCenterProfile.center_id == center_id,
        LearningCenterProfile.role_in_center == UserRole.STUDENT
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Student not found")
    
    profile.full_name = student_data.full_name
    db.commit()
    
    return APIResponse.success({"message": "Student updated successfully"})


@router.delete("/users/students/{profile_id}")
def delete_student(
        profile_id: int,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Soft delete student"""
    center_id = current_user["center_id"]
    
    profile = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.id == profile_id,
        LearningCenterProfile.center_id == center_id,
        LearningCenterProfile.role_in_center == UserRole.STUDENT
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Student not found")
    
    profile.is_active = False
    db.commit()
    
    return APIResponse.success({"message": "Student deleted successfully"})


# Teacher Management CRUD
@router.put("/users/teachers/{profile_id}")
def update_teacher(
        profile_id: int,
        teacher_data: schemas.TeacherUpdate,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Update teacher information"""
    center_id = current_user["center_id"]
    
    profile = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.id == profile_id,
        LearningCenterProfile.center_id == center_id,
        LearningCenterProfile.role_in_center == UserRole.TEACHER
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    profile.full_name = teacher_data.full_name
    
    # Update password if provided
    if teacher_data.password:
        user = db.query(User).filter(User.id == profile.user_id).first()
        if user:
            user.password_hash = hash_password(teacher_data.password)
    
    db.commit()
    
    return APIResponse.success({"message": "Teacher updated successfully"})


@router.delete("/users/teachers/{profile_id}")
def delete_teacher(
        profile_id: int,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Soft delete teacher"""
    center_id = current_user["center_id"]
    
    profile = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.id == profile_id,
        LearningCenterProfile.center_id == center_id,
        LearningCenterProfile.role_in_center == UserRole.TEACHER
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    profile.is_active = False
    db.commit()
    
    return APIResponse.success({"message": "Teacher deleted successfully"})


# Password Management
@router.patch("/password")
def change_admin_password(
        password_data: schemas.AdminPasswordChangeRequest,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Change admin user password"""
    # Get current admin user
    admin_user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not admin_user:
        raise HTTPException(status_code=404, detail="Admin user not found")

    # Update password
    admin_user.password_hash = hash_password(password_data.new_password)
    db.commit()

    return APIResponse.success({"message": "Password updated successfully"})


# Analytics
@router.get("/analytics/overview")
def get_analytics_overview(
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Get learning center analytics"""
    # Allow admin, teacher, and student access
    if current_user["role"] not in ["admin", "teacher", "student"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
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


# Course CRUD
@router.get("/courses")
def get_courses(
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Get all courses in center"""
    center_id = current_user["center_id"]
    
    courses = db.query(Course).filter(
        Course.center_id == center_id,
        Course.is_active == True
    ).all()
    
    return APIResponse.success([{
        "id": c.id,
        "title": c.title,
        "description": c.description,
        "created_at": c.created_at
    } for c in courses])


@router.put("/courses/{course_id}")
def update_course(
        course_id: int,
        course_data: schemas.CourseCreate,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Update course"""
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.center_id == current_user["center_id"]
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    course.title = course_data.title
    course.description = course_data.description
    db.commit()
    
    ContentService.invalidate_center_cache(current_user["center_id"])
    
    return APIResponse.success({"message": "Course updated successfully"})


@router.delete("/courses/{course_id}")
def delete_course(
        course_id: int,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Soft delete course"""
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.center_id == current_user["center_id"]
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    course.is_active = False
    db.commit()
    
    ContentService.invalidate_center_cache(current_user["center_id"])
    
    return APIResponse.success({"message": "Course deleted successfully"})


# Module CRUD
@router.get("/courses/{course_id}/modules")
def get_modules(
        course_id: int,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Get all modules in course"""
    # Verify course belongs to center
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.center_id == current_user["center_id"]
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    modules = db.query(Module).filter(
        Module.course_id == course_id,
        Module.is_active == True
    ).order_by(Module.order_index).all()
    
    return APIResponse.success([{
        "id": m.id,
        "title": m.title,
        "description": m.description,
        "order_index": m.order_index,
        "created_at": m.created_at
    } for m in modules])


@router.put("/modules/{module_id}")
def update_module(
        module_id: int,
        module_data: schemas.ModuleUpdate,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Update module"""
    # Verify module belongs to center
    module = db.query(Module).join(Course).filter(
        Module.id == module_id,
        Course.center_id == current_user["center_id"]
    ).first()
    
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    module.title = module_data.title
    module.description = module_data.description
    module.order_index = module_data.order_index
    db.commit()
    
    ContentService.invalidate_center_cache(current_user["center_id"])
    
    return APIResponse.success({"message": "Module updated successfully"})


@router.delete("/modules/{module_id}")
def delete_module(
        module_id: int,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Soft delete module"""
    # Verify module belongs to center
    module = db.query(Module).join(Course).filter(
        Module.id == module_id,
        Course.center_id == current_user["center_id"]
    ).first()
    
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    module.is_active = False
    db.commit()
    
    ContentService.invalidate_center_cache(current_user["center_id"])
    
    return APIResponse.success({"message": "Module deleted successfully"})


# Lesson CRUD
@router.get("/modules/{module_id}/lessons")
def get_lessons(
        module_id: int,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Get all lessons in module"""
    # Verify module belongs to center
    module = db.query(Module).join(Course).filter(
        Module.id == module_id,
        Course.center_id == current_user["center_id"]
    ).first()
    
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    lessons = db.query(Lesson).filter(
        Lesson.module_id == module_id,
        Lesson.is_active == True
    ).order_by(Lesson.order_index).all()
    
    return APIResponse.success([{
        "id": l.id,
        "title": l.title,
        "description": l.description,
        "order_index": l.order_index,
        "created_at": l.created_at
    } for l in lessons])


@router.put("/lessons/{lesson_id}")
def update_lesson(
        lesson_id: int,
        lesson_data: schemas.LessonUpdate,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Update lesson"""
    # Verify lesson belongs to center
    lesson = db.query(Lesson).join(Module).join(Course).filter(
        Lesson.id == lesson_id,
        Course.center_id == current_user["center_id"]
    ).first()
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    lesson.title = lesson_data.title
    lesson.description = lesson_data.description
    lesson.order_index = lesson_data.order_index
    db.commit()
    
    ContentService.invalidate_center_cache(current_user["center_id"])
    
    return APIResponse.success({"message": "Lesson updated successfully"})


@router.delete("/lessons/{lesson_id}")
def delete_lesson(
        lesson_id: int,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Soft delete lesson"""
    # Verify lesson belongs to center
    lesson = db.query(Lesson).join(Module).join(Course).filter(
        Lesson.id == lesson_id,
        Course.center_id == current_user["center_id"]
    ).first()
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    lesson.is_active = False
    db.commit()
    
    ContentService.invalidate_center_cache(current_user["center_id"])
    
    return APIResponse.success({"message": "Lesson deleted successfully"})


# Word CRUD with File Upload
@router.get("/lessons/{lesson_id}/words")
def get_words(
        lesson_id: int,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Get all words in lesson"""
    # Verify lesson belongs to center
    lesson = db.query(Lesson).join(Module).join(Course).filter(
        Lesson.id == lesson_id,
        Course.center_id == current_user["center_id"]
    ).first()
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    words = db.query(Word).filter(
        Word.lesson_id == lesson_id,
        Word.is_active == True
    ).order_by(Word.order_index).all()
    
    return APIResponse.success([{
        "id": w.id,
        "word": w.word,
        "meaning": w.meaning,
        "definition": w.definition,
        "example_sentence": w.example_sentence,
        "image_url": w.image_url,
        "audio_url": w.audio_url,
        "order_index": w.order_index,
        "created_at": w.created_at
    } for w in words])


@router.put("/words/{word_id}")
def update_word(
        word_id: int,
        word_data: schemas.WordUpdate,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Update word"""
    # Verify word belongs to center
    word = db.query(Word).join(Lesson).join(Module).join(Course).filter(
        Word.id == word_id,
        Course.center_id == current_user["center_id"]
    ).first()
    
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    
    word.word = word_data.word
    word.meaning = word_data.meaning
    word.definition = word_data.definition
    word.example_sentence = word_data.example_sentence
    word.order_index = word_data.order_index
    db.commit()
    
    ContentService.invalidate_center_cache(current_user["center_id"])
    
    return APIResponse.success({"message": "Word updated successfully"})


@router.delete("/words/{word_id}")
def delete_word(
        word_id: int,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Soft delete word"""
    # Verify word belongs to center
    word = db.query(Word).join(Lesson).join(Module).join(Course).filter(
        Word.id == word_id,
        Course.center_id == current_user["center_id"]
    ).first()
    
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    
    word.is_active = False
    db.commit()
    
    ContentService.invalidate_center_cache(current_user["center_id"])
    
    return APIResponse.success({"message": "Word deleted successfully"})


@router.post("/words/{word_id}/image")
def upload_word_image(
        word_id: int,
        file: UploadFile = File(...),
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Upload image for word (max 1MB)"""
    # Verify word belongs to center
    word = db.query(Word).join(Lesson).join(Module).join(Course).filter(
        Word.id == word_id,
        Course.center_id == current_user["center_id"]
    ).first()
    
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Check file size - max 1MB
    file_content = file.file.read()
    if len(file_content) > 1 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image size must be less than 1MB")
    
    # Reset file pointer
    file.file.seek(0)
    
    # Save file
    file_path = save_uploaded_file(file, "word-images")
    word.image_url = file_path
    db.commit()
    
    ContentService.invalidate_center_cache(current_user["center_id"])
    
    return APIResponse.success({"message": "Word image uploaded successfully", "image_url": file_path})


@router.post("/words/{word_id}/audio")
def upload_word_audio(
        word_id: int,
        file: UploadFile = File(...),
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Upload audio for word (max 7 seconds, 1MB)"""
    # Verify word belongs to center
    word = db.query(Word).join(Lesson).join(Module).join(Course).filter(
        Word.id == word_id,
        Course.center_id == current_user["center_id"]
    ).first()
    
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    
    # Validate file type
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio file")
    
    # Save to temporary file to check duration
    import tempfile
    from mutagen import File as MutagenFile
    
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        content = file.file.read()
        
        # Check file size - max 1MB
        if len(content) > 1 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Audio size must be less than 1MB")
            
        temp_file.write(content)
        temp_file.flush()
        
        try:
            # Check audio duration
            audio_file = MutagenFile(temp_file.name)
            if audio_file is None:
                raise HTTPException(status_code=400, detail="Invalid audio file format")
            
            duration = audio_file.info.length
            if duration > 7.0:
                raise HTTPException(status_code=400, detail="Audio duration must be 7 seconds or less")
                
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Audio validation failed: {str(e)}")
        finally:
            os.unlink(temp_file.name)
    
    # Reset file pointer
    file.file.seek(0)
    
    # Save file
    file_path = save_uploaded_file(file, "word-audio")
    word.audio_url = file_path
    db.commit()
    
    ContentService.invalidate_center_cache(current_user["center_id"])
    
    return APIResponse.success({"message": "Word audio uploaded successfully", "audio_url": file_path})


# Payment History
@router.get("/payments")
def get_center_payments(
        page: int = 1,
        size: int = 20,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Get payment history for center"""
    center_id = current_user["center_id"]
    
    query = db.query(Payment).filter(Payment.center_id == center_id)
    query = query.order_by(desc(Payment.created_at))
    result = paginate(query, page, size)
    
    payments = [{
        "id": p.id,
        "amount": p.amount,
        "days_added": p.days_added,
        "description": p.description,
        "created_at": p.created_at
    } for p in result["items"]]
    
    return APIResponse.paginated(payments, result["total"], result["page"], result["size"])


# Learning Center Info & Update
@router.get("/center/info")
def get_center_info(
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Get basic learning center information"""
    center_id = current_user["center_id"]
    
    center = db.query(LearningCenter).filter(LearningCenter.id == center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")
    
    return APIResponse.success({
        "id": center.id,
        "title": center.title,
        "logo": center.logo,
        "student_limit": center.student_limit,
        "days_remaining": center.days_remaining,
        "is_active": center.is_active,
        "created_at": center.created_at
    })


@router.patch("/center")
def update_center(
        center_data: schemas.LearningCenterUpdate,
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Update learning center title only"""
    center_id = current_user["center_id"]
    
    center = db.query(LearningCenter).filter(LearningCenter.id == center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")
    
    center.title = center_data.title
    db.commit()
    
    return APIResponse.success({"message": "Center updated successfully"})


@router.post("/center/logo")
def upload_center_logo(
        file: UploadFile = File(...),
        current_user: dict = Depends(get_admin_user),
        db: Session = Depends(get_db)
):
    """Upload logo for learning center (PNG only, max 3MB)"""
    center_id = current_user["center_id"]
    
    center = db.query(LearningCenter).filter(LearningCenter.id == center_id).first()
    if not center:
        raise HTTPException(status_code=404, detail="Center not found")
    
    # Validate file type - PNG only
    if file.content_type != "image/png":
        raise HTTPException(status_code=400, detail="Only PNG files are allowed")
    
    # Read file content to check size
    file_content = file.file.read()
    file_size = len(file_content)
    
    # Check file size - max 3MB
    if file_size > 3 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 3MB")
    
    # Reset file pointer
    file.file.seek(0)
    
    # Save file
    file_path = save_uploaded_file(file, "logos")
    center.logo = file_path
    db.commit()
    
    return APIResponse.success({"message": "Center logo uploaded successfully", "logo_url": file_path})



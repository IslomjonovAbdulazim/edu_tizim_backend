from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ..database import get_db
from ..models import *
from ..services import LeaderboardService
from ..utils import APIResponse, check_center_active, get_current_user_data
from ..dependencies import get_current_user
from .. import schemas

router = APIRouter()


def get_teacher_user(current_user: dict = Depends(get_current_user)):
    """Require teacher role"""
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")
    if not current_user["center_id"]:
        raise HTTPException(status_code=403, detail="No center access")
    return current_user


@router.get("/dashboard")
def teacher_dashboard(
        current_user: dict = Depends(get_teacher_user),
        db: Session = Depends(get_db)
):
    """Teacher dashboard with assigned groups overview"""
    profile_id = current_user["profile"].id
    center_id = current_user["center_id"]

    check_center_active(center_id, db)

    # Get assigned groups
    assigned_groups = db.query(Group).filter(
        Group.teacher_id == profile_id,
        Group.is_active == True
    ).all()

    # Count total students
    total_students = db.query(GroupMember).join(Group).filter(
        Group.teacher_id == profile_id,
        Group.is_active == True
    ).count()

    # Get recent progress from my students
    recent_progress = db.query(Progress).join(LearningCenterProfile).join(
        GroupMember
    ).join(Group).filter(
        Group.teacher_id == profile_id,
        Group.is_active == True
    ).order_by(Progress.last_practiced.desc()).limit(10).all()

    return APIResponse.success({
        "teacher": {
            "id": current_user["profile"].id,
            "full_name": current_user["profile"].full_name
        },
        "stats": {
            "assigned_groups": len(assigned_groups),
            "total_students": total_students
        },
        "groups": [{
            "id": g.id,
            "name": g.name,
            "course_id": g.course_id,
            "created_at": g.created_at
        } for g in assigned_groups],
        "recent_activity": [{
            "lesson_id": p.lesson_id,
            "percentage": p.percentage,
            "completed": p.completed,
            "last_practiced": p.last_practiced
        } for p in recent_progress]
    })


@router.get("/groups")
def get_my_groups(
        current_user: dict = Depends(get_teacher_user),
        db: Session = Depends(get_db)
):
    """Get groups assigned to teacher"""
    profile_id = current_user["profile"].id

    groups = db.query(Group).filter(
        Group.teacher_id == profile_id,
        Group.is_active == True
    ).all()

    # Add student count to each group
    groups_with_stats = []
    for group in groups:
        student_count = db.query(GroupMember).filter(
            GroupMember.group_id == group.id
        ).count()

        group_data = {
            "id": group.id,
            "name": group.name,
            "course_id": group.course_id,
            "student_count": student_count,
            "created_at": group.created_at
        }
        groups_with_stats.append(group_data)

    return APIResponse.success(groups_with_stats)


@router.get("/groups/{group_id}/students")
def get_group_students(
        group_id: int,
        current_user: dict = Depends(get_teacher_user),
        db: Session = Depends(get_db)
):
    """Get students in a specific group"""
    profile_id = current_user["profile"].id

    # Check if teacher is assigned to this group
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.teacher_id == profile_id
    ).first()

    if not group:
        raise HTTPException(status_code=403, detail="Not authorized for this group")

    # Get students with their progress
    students = db.query(LearningCenterProfile).join(GroupMember).filter(
        GroupMember.group_id == group_id,
        LearningCenterProfile.is_active == True
    ).all()

    students_with_progress = []
    for student in students:
        # Get progress summary
        total_progress = db.query(Progress).filter(
            Progress.profile_id == student.id
        ).all()

        completed_lessons = len([p for p in total_progress if p.completed])
        avg_percentage = sum(p.percentage for p in total_progress) / max(len(total_progress), 1)

        # Total coins
        total_coins = db.query(func.sum(Coin.amount)).filter(
            Coin.profile_id == student.id
        ).scalar() or 0

        student_data = {
            "profile": {
                "id": student.id,
                "full_name": student.full_name,
                "created_at": student.created_at
            },
            "progress": {
                "completed_lessons": completed_lessons,
                "total_lessons": len(total_progress),
                "average_percentage": round(avg_percentage, 2),
                "total_coins": total_coins,
                "total_points": total_coins
            }
        }
        students_with_progress.append(student_data)

    # Sort students by points (descending) and add rank
    students_with_progress.sort(key=lambda x: x["progress"]["total_points"], reverse=True)
    
    for i, student in enumerate(students_with_progress):
        student["rank"] = i + 1

    return APIResponse.success({
        "group": {
            "id": group.id,
            "name": group.name,
            "course_id": group.course_id
        },
        "students": students_with_progress
    })


@router.get("/students/{student_id}/progress")
def get_student_progress(
        student_id: int,
        current_user: dict = Depends(get_teacher_user),
        db: Session = Depends(get_db)
):
    """Get detailed progress for a specific student"""
    profile_id = current_user["profile"].id

    # Check if teacher has access to this student
    has_access = db.query(GroupMember).join(Group).filter(
        GroupMember.profile_id == student_id,
        Group.teacher_id == profile_id
    ).first()

    if not has_access:
        raise HTTPException(status_code=403, detail="No access to this student")

    student = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.id == student_id
    ).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Get detailed progress
    progress_records = db.query(Progress).filter(
        Progress.profile_id == student_id
    ).all()

    # Get word progress for weak words with word details
    weak_words = db.query(WordProgress, Word).join(
        Word, WordProgress.word_id == Word.id
    ).filter(
        WordProgress.profile_id == student_id,
        WordProgress.last_seven_attempts.like('%0%')
    ).limit(20).all()

    # Recent activity
    recent_coins = db.query(Coin).filter(
        Coin.profile_id == student_id
    ).order_by(Coin.earned_at.desc()).limit(10).all()

    return APIResponse.success({
        "student": {
            "id": student.id,
            "full_name": student.full_name,
            "created_at": student.created_at
        },
        "progress": [{
            "lesson_id": p.lesson_id,
            "percentage": p.percentage,
            "completed": p.completed,
            "last_practiced": p.last_practiced
        } for p in progress_records],
        "weak_words": [{
            "word_id": w.WordProgress.word_id,
            "word": w.Word.word,
            "meaning": w.Word.meaning,
            "last_seven_attempts": w.WordProgress.last_seven_attempts,
            "total_correct": w.WordProgress.total_correct,
            "total_attempts": w.WordProgress.total_attempts
        } for w in weak_words],
        "recent_activity": [{
            "amount": c.amount,
            "source": c.source,
            "earned_at": c.earned_at
        } for c in recent_coins]
    })


@router.get("/groups/{group_id}/leaderboard")
def get_group_leaderboard(
        group_id: int,
        current_user: dict = Depends(get_teacher_user),
        db: Session = Depends(get_db)
):
    """Get leaderboard for specific group"""
    profile_id = current_user["profile"].id

    # Check if teacher is assigned to this group
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.teacher_id == profile_id
    ).first()

    if not group:
        raise HTTPException(status_code=403, detail="Not authorized for this group")

    leaderboard = LeaderboardService.get_group_leaderboard(db, group_id)

    return APIResponse.success({
        "group": {
            "id": group.id,
            "name": group.name
        },
        "leaderboard": leaderboard
    })


@router.get("/analytics/overview")
def get_teacher_analytics(
        current_user: dict = Depends(get_teacher_user),
        db: Session = Depends(get_db)
):
    """Get analytics overview for teacher's groups"""
    profile_id = current_user["profile"].id

    # Get all assigned groups
    groups = db.query(Group).filter(
        Group.teacher_id == profile_id,
        Group.is_active == True
    ).all()

    group_ids = [g.id for g in groups]

    # Total students across all groups
    total_students = db.query(GroupMember).filter(
        GroupMember.group_id.in_(group_ids)
    ).count() if group_ids else 0

    # Active students (those who practiced in last 7 days)
    week_ago = datetime.now() - timedelta(days=7)
    active_students = db.query(Progress.profile_id).join(
        GroupMember, GroupMember.profile_id == Progress.profile_id
    ).filter(
        GroupMember.group_id.in_(group_ids),
        Progress.last_practiced >= week_ago
    ).distinct().count() if group_ids else 0

    # Average completion rate
    all_progress = []
    if group_ids:
        all_progress = db.query(Progress).join(
            LearningCenterProfile, Progress.profile_id == LearningCenterProfile.id
        ).join(
            GroupMember, GroupMember.profile_id == LearningCenterProfile.id
        ).filter(
            GroupMember.group_id.in_(group_ids)
        ).all()

    if all_progress:
        avg_completion = sum(p.percentage for p in all_progress) / len(all_progress)
        completed_lessons = len([p for p in all_progress if p.completed])
    else:
        avg_completion = 0
        completed_lessons = 0

    return APIResponse.success({
        "total_groups": len(groups),
        "total_students": total_students,
        "active_students": active_students,
        "avg_completion_rate": round(avg_completion, 2),
        "completed_lessons": completed_lessons,
        "total_lessons": len(all_progress)
    })


@router.get("/students/struggling")
def get_struggling_students(
        current_user: dict = Depends(get_teacher_user),
        db: Session = Depends(get_db)
):
    """Get students who need attention (low progress/activity)"""
    profile_id = current_user["profile"].id

    # Get students from teacher's groups
    students = db.query(LearningCenterProfile).join(GroupMember).join(Group).filter(
        Group.teacher_id == profile_id,
        Group.is_active == True,
        LearningCenterProfile.is_active == True
    ).all()

    struggling_students = []

    for student in students:
        # Check progress
        progress_records = db.query(Progress).filter(
            Progress.profile_id == student.id
        ).all()

        if not progress_records:
            struggling_students.append({
                "student": {
                    "id": student.id,
                    "full_name": student.full_name
                },
                "reason": "No progress recorded",
                "avg_percentage": 0
            })
            continue

        avg_percentage = sum(p.percentage for p in progress_records) / len(progress_records)

        # Students with less than 50% average
        if avg_percentage < 50:
            struggling_students.append({
                "student": {
                    "id": student.id,
                    "full_name": student.full_name
                },
                "reason": "Low completion rate",
                "avg_percentage": round(avg_percentage, 2)
            })

        # Check for inactivity (no activity in last 3 days)
        three_days_ago = datetime.now() - timedelta(days=3)
        recent_activity = any(p.last_practiced >= three_days_ago for p in progress_records)

        if not recent_activity:
            struggling_students.append({
                "student": {
                    "id": student.id,
                    "full_name": student.full_name
                },
                "reason": "No recent activity",
                "avg_percentage": round(avg_percentage, 2)
            })

    return APIResponse.success(struggling_students)


@router.get("/reports/weekly")
def get_weekly_report(
        current_user: dict = Depends(get_teacher_user),
        db: Session = Depends(get_db)
):
    """Get weekly activity report for teacher's groups"""
    profile_id = current_user["profile"].id

    week_ago = datetime.now() - timedelta(days=7)

    # Get progress in last week from teacher's students
    weekly_progress = db.query(Progress).join(LearningCenterProfile).join(
        GroupMember
    ).join(Group).filter(
        Group.teacher_id == profile_id,
        Progress.last_practiced >= week_ago
    ).all()

    # Group by day
    daily_activity = {}
    for progress in weekly_progress:
        day = progress.last_practiced.strftime('%Y-%m-%d')
        if day not in daily_activity:
            daily_activity[day] = {
                "date": day,
                "lessons_completed": 0,
                "active_students": set()
            }

        if progress.completed:
            daily_activity[day]["lessons_completed"] += 1

        daily_activity[day]["active_students"].add(progress.profile_id)

    # Convert sets to counts
    for day_data in daily_activity.values():
        day_data["active_students"] = len(day_data["active_students"])

    return APIResponse.success({
        "week_summary": {
            "total_progress_records": len(weekly_progress),
            "daily_breakdown": sorted(daily_activity.values(), key=lambda x: x["date"])
        }
    })


@router.get("/students/{student_id}/modules")
def get_student_modules(
        student_id: int,
        current_user: dict = Depends(get_teacher_user),
        db: Session = Depends(get_db)
):
    """Get student's course modules with progress statistics"""
    profile_id = current_user["profile"].id
    
    # Check if teacher has access to this student
    has_access = db.query(GroupMember).join(Group).filter(
        GroupMember.profile_id == student_id,
        Group.teacher_id == profile_id
    ).first()
    
    if not has_access:
        raise HTTPException(status_code=403, detail="No access to this student")
    
    student = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.id == student_id
    ).first()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Get student's course
    group_member = db.query(GroupMember).join(Group).filter(
        GroupMember.profile_id == student_id,
        Group.teacher_id == profile_id
    ).first()
    
    if not group_member or not group_member.group.course_id:
        raise HTTPException(status_code=404, detail="Student course not found")
    
    course_id = group_member.group.course_id
    
    # Get course info
    course = db.query(Course).filter(Course.id == course_id).first()
    
    # Get all modules for the course
    modules = db.query(Module).filter(
        Module.course_id == course_id,
        Module.is_active == True
    ).order_by(Module.order_index).all()
    
    modules_data = []
    total_course_progress = 0
    total_completed_lessons = 0
    total_lessons = 0
    
    for module in modules:
        # Get lesson count for this module
        lesson_count = db.query(Lesson).filter(
            Lesson.module_id == module.id,
            Lesson.is_active == True
        ).count()
        
        # Get progress for lessons in this module
        module_progress = db.query(Progress).join(Lesson).filter(
            Progress.profile_id == student_id,
            Lesson.module_id == module.id,
            Lesson.is_active == True
        ).all()
        
        completed_lessons = len([p for p in module_progress if p.completed])
        module_avg_percentage = sum(p.percentage for p in module_progress) / max(len(module_progress), 1) if module_progress else 0
        
        total_course_progress += module_avg_percentage
        total_completed_lessons += completed_lessons
        total_lessons += lesson_count
        
        module_data = {
            "id": module.id,
            "title": module.title,
            "description": module.description,
            "order_index": module.order_index,
            "progress": {
                "percentage": round(module_avg_percentage, 2),
                "completed_lessons": completed_lessons,
                "total_lessons": lesson_count
            }
        }
        
        modules_data.append(module_data)
    
    # Calculate overall course progress
    overall_percentage = round(total_course_progress / max(len(modules_data), 1), 2)
    
    return APIResponse.success({
        "student": {
            "id": student.id,
            "full_name": student.full_name,
            "created_at": student.created_at
        },
        "course": {
            "id": course_id,
            "title": course.title,
            "description": course.description,
            "progress": {
                "overall_percentage": overall_percentage,
                "completed_lessons": total_completed_lessons,
                "total_lessons": total_lessons
            }
        },
        "modules": modules_data
    })


@router.get("/students/{student_id}/modules/{module_id}/lessons")
def get_student_module_lessons(
        student_id: int,
        module_id: int,
        current_user: dict = Depends(get_teacher_user),
        db: Session = Depends(get_db)
):
    """Get lessons in a specific module with progress"""
    profile_id = current_user["profile"].id
    
    # Check if teacher has access to this student
    has_access = db.query(GroupMember).join(Group).filter(
        GroupMember.profile_id == student_id,
        Group.teacher_id == profile_id
    ).first()
    
    if not has_access:
        raise HTTPException(status_code=403, detail="No access to this student")
    
    # Verify module belongs to student's course
    student_course = db.query(Course).join(Group).join(GroupMember).filter(
        GroupMember.profile_id == student_id,
        Group.teacher_id == profile_id
    ).first()
    
    if not student_course:
        raise HTTPException(status_code=404, detail="Student course not found")
    
    module = db.query(Module).filter(
        Module.id == module_id,
        Module.course_id == student_course.id,
        Module.is_active == True
    ).first()
    
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    # Get lessons for this module
    lessons = db.query(Lesson).filter(
        Lesson.module_id == module_id,
        Lesson.is_active == True
    ).order_by(Lesson.order_index).all()
    
    lessons_data = []
    
    for lesson in lessons:
        # Get lesson progress
        lesson_progress = db.query(Progress).filter(
            Progress.profile_id == student_id,
            Progress.lesson_id == lesson.id
        ).first()
        
        lesson_percentage = lesson_progress.percentage if lesson_progress else 0
        lesson_completed = lesson_progress.completed if lesson_progress else False
        lesson_last_practiced = lesson_progress.last_practiced if lesson_progress else None
        
        # Get word count and weak words count for this lesson
        word_count = db.query(Word).filter(
            Word.lesson_id == lesson.id,
            Word.is_active == True
        ).count()
        
        weak_words_count = db.query(WordProgress).join(Word).filter(
            Word.lesson_id == lesson.id,
            WordProgress.profile_id == student_id,
            WordProgress.last_seven_attempts.like('%0%'),
            Word.is_active == True
        ).count()
        
        practiced_words_count = db.query(WordProgress).join(Word).filter(
            Word.lesson_id == lesson.id,
            WordProgress.profile_id == student_id,
            WordProgress.total_attempts > 0,
            Word.is_active == True
        ).count()
        
        lesson_data = {
            "id": lesson.id,
            "title": lesson.title,
            "description": lesson.description,
            "order_index": lesson.order_index,
            "progress": {
                "percentage": lesson_percentage,
                "completed": lesson_completed,
                "last_practiced": lesson_last_practiced
            },
            "word_stats": {
                "total_words": word_count,
                "weak_words_count": weak_words_count,
                "practiced_words": practiced_words_count
            }
        }
        
        lessons_data.append(lesson_data)
    
    return APIResponse.success({
        "module": {
            "id": module.id,
            "title": module.title,
            "description": module.description,
            "order_index": module.order_index
        },
        "lessons": lessons_data
    })


@router.get("/students/{student_id}/lessons/{lesson_id}/words")
def get_student_lesson_words(
        student_id: int,
        lesson_id: int,
        current_user: dict = Depends(get_teacher_user),
        db: Session = Depends(get_db)
):
    """Get words in a specific lesson with detailed statistics"""
    profile_id = current_user["profile"].id
    
    # Check if teacher has access to this student
    has_access = db.query(GroupMember).join(Group).filter(
        GroupMember.profile_id == student_id,
        Group.teacher_id == profile_id
    ).first()
    
    if not has_access:
        raise HTTPException(status_code=403, detail="No access to this student")
    
    # Verify lesson belongs to student's course
    lesson = db.query(Lesson).join(Module).join(Course).join(Group).join(GroupMember).filter(
        GroupMember.profile_id == student_id,
        Group.teacher_id == profile_id,
        Lesson.id == lesson_id,
        Lesson.is_active == True
    ).first()
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Get words for this lesson
    words = db.query(Word).filter(
        Word.lesson_id == lesson_id,
        Word.is_active == True
    ).order_by(Word.order_index).all()
    
    words_data = []
    
    for word in words:
        # Get word progress
        word_progress = db.query(WordProgress).filter(
            WordProgress.profile_id == student_id,
            WordProgress.word_id == word.id
        ).first()
        
        if word_progress:
            # Calculate success rate from last 7 attempts
            last_seven = word_progress.last_seven_attempts
            correct_in_seven = last_seven.count('1') if last_seven else 0
            total_in_seven = len(last_seven) if last_seven else 0
            
            word_data = {
                "id": word.id,
                "word": word.word,
                "meaning": word.meaning,
                "definition": word.definition,
                "example_sentence": word.example_sentence,
                "image_url": word.image_url,
                "audio_url": word.audio_url,
                "order_index": word.order_index,
                "stats": {
                    "total_attempts": word_progress.total_attempts,
                    "total_correct": word_progress.total_correct,
                    "accuracy_rate": round((word_progress.total_correct / max(word_progress.total_attempts, 1)) * 100, 2),
                    "last_seven_attempts": word_progress.last_seven_attempts,
                    "recent_accuracy": round((correct_in_seven / max(total_in_seven, 1)) * 100, 2),
                    "last_practiced": word_progress.last_practiced,
                    "is_weak": '0' in (word_progress.last_seven_attempts or "")
                }
            }
        else:
            word_data = {
                "id": word.id,
                "word": word.word,
                "meaning": word.meaning,
                "definition": word.definition,
                "example_sentence": word.example_sentence,
                "image_url": word.image_url,
                "audio_url": word.audio_url,
                "order_index": word.order_index,
                "stats": {
                    "total_attempts": 0,
                    "total_correct": 0,
                    "accuracy_rate": 0,
                    "last_seven_attempts": "",
                    "recent_accuracy": 0,
                    "last_practiced": None,
                    "is_weak": False
                }
            }
        
        words_data.append(word_data)
    
    # Calculate lesson stats
    weak_words_count = len([w for w in words_data if w["stats"]["is_weak"]])
    practiced_words = len([w for w in words_data if w["stats"]["total_attempts"] > 0])
    mastered_words = len([w for w in words_data if w["stats"]["accuracy_rate"] >= 80])
    
    # Get lesson progress
    lesson_progress = db.query(Progress).filter(
        Progress.profile_id == student_id,
        Progress.lesson_id == lesson_id
    ).first()
    
    return APIResponse.success({
        "lesson": {
            "id": lesson.id,
            "title": lesson.title,
            "description": lesson.description,
            "order_index": lesson.order_index,
            "progress": {
                "percentage": lesson_progress.percentage if lesson_progress else 0,
                "completed": lesson_progress.completed if lesson_progress else False,
                "last_practiced": lesson_progress.last_practiced if lesson_progress else None
            }
        },
        "words": words_data,
        "summary": {
            "total_words": len(words_data),
            "weak_words_count": weak_words_count,
            "practiced_words": practiced_words,
            "mastered_words": mastered_words
        }
    })


@router.get("/students/{student_id}/detailed-progress")
def get_student_detailed_progress(
        student_id: int,
        current_user: dict = Depends(get_teacher_user),
        db: Session = Depends(get_db)
):
    """Get comprehensive student progress with modules, lessons, and word statistics"""
    profile_id = current_user["profile"].id
    
    # Check if teacher has access to this student
    has_access = db.query(GroupMember).join(Group).filter(
        GroupMember.profile_id == student_id,
        Group.teacher_id == profile_id
    ).first()
    
    if not has_access:
        raise HTTPException(status_code=403, detail="No access to this student")
    
    student = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.id == student_id
    ).first()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Get student's group and course
    group_member = db.query(GroupMember).join(Group).filter(
        GroupMember.profile_id == student_id,
        Group.teacher_id == profile_id
    ).first()
    
    if not group_member or not group_member.group.course_id:
        raise HTTPException(status_code=404, detail="Student course not found")
    
    course_id = group_member.group.course_id
    
    # Get all modules for the course
    modules = db.query(Module).filter(
        Module.course_id == course_id,
        Module.is_active == True
    ).order_by(Module.order_index).all()
    
    modules_data = []
    
    for module in modules:
        # Get lessons for this module
        lessons = db.query(Lesson).filter(
            Lesson.module_id == module.id,
            Lesson.is_active == True
        ).order_by(Lesson.order_index).all()
        
        lessons_data = []
        module_total_progress = 0
        module_completed_lessons = 0
        
        for lesson in lessons:
            # Get lesson progress
            lesson_progress = db.query(Progress).filter(
                Progress.profile_id == student_id,
                Progress.lesson_id == lesson.id
            ).first()
            
            lesson_percentage = lesson_progress.percentage if lesson_progress else 0
            lesson_completed = lesson_progress.completed if lesson_progress else False
            lesson_last_practiced = lesson_progress.last_practiced if lesson_progress else None
            
            if lesson_completed:
                module_completed_lessons += 1
            module_total_progress += lesson_percentage
            
            # Get words for this lesson
            words = db.query(Word).filter(
                Word.lesson_id == lesson.id,
                Word.is_active == True
            ).order_by(Word.order_index).all()
            
            words_data = []
            
            for word in words:
                # Get word progress
                word_progress = db.query(WordProgress).filter(
                    WordProgress.profile_id == student_id,
                    WordProgress.word_id == word.id
                ).first()
                
                if word_progress:
                    # Calculate success rate from last 7 attempts
                    last_seven = word_progress.last_seven_attempts
                    correct_in_seven = last_seven.count('1') if last_seven else 0
                    total_in_seven = len(last_seven) if last_seven else 0
                    
                    word_data = {
                        "id": word.id,
                        "word": word.word,
                        "meaning": word.meaning,
                        "definition": word.definition,
                        "example_sentence": word.example_sentence,
                        "image_url": word.image_url,
                        "audio_url": word.audio_url,
                        "order_index": word.order_index,
                        "stats": {
                            "total_attempts": word_progress.total_attempts,
                            "total_correct": word_progress.total_correct,
                            "accuracy_rate": round((word_progress.total_correct / max(word_progress.total_attempts, 1)) * 100, 2),
                            "last_seven_attempts": word_progress.last_seven_attempts,
                            "recent_accuracy": round((correct_in_seven / max(total_in_seven, 1)) * 100, 2),
                            "last_practiced": word_progress.last_practiced,
                            "is_weak": '0' in (word_progress.last_seven_attempts or "")
                        }
                    }
                else:
                    word_data = {
                        "id": word.id,
                        "word": word.word,
                        "meaning": word.meaning,
                        "definition": word.definition,
                        "example_sentence": word.example_sentence,
                        "image_url": word.image_url,
                        "audio_url": word.audio_url,
                        "order_index": word.order_index,
                        "stats": {
                            "total_attempts": 0,
                            "total_correct": 0,
                            "accuracy_rate": 0,
                            "last_seven_attempts": "",
                            "recent_accuracy": 0,
                            "last_practiced": None,
                            "is_weak": False
                        }
                    }
                
                words_data.append(word_data)
            
            lesson_data = {
                "id": lesson.id,
                "title": lesson.title,
                "description": lesson.description,
                "order_index": lesson.order_index,
                "progress": {
                    "percentage": lesson_percentage,
                    "completed": lesson_completed,
                    "last_practiced": lesson_last_practiced
                },
                "words": words_data,
                "word_stats": {
                    "total_words": len(words_data),
                    "weak_words_count": len([w for w in words_data if w["stats"]["is_weak"]]),
                    "practiced_words": len([w for w in words_data if w["stats"]["total_attempts"] > 0]),
                    "mastered_words": len([w for w in words_data if w["stats"]["accuracy_rate"] >= 80])
                }
            }
            
            lessons_data.append(lesson_data)
        
        # Calculate module progress percentage
        module_percentage = round(module_total_progress / max(len(lessons), 1), 2)
        
        module_data = {
            "id": module.id,
            "title": module.title,
            "description": module.description,
            "order_index": module.order_index,
            "progress": {
                "percentage": module_percentage,
                "completed_lessons": module_completed_lessons,
                "total_lessons": len(lessons)
            },
            "lessons": lessons_data
        }
        
        modules_data.append(module_data)
    
    # Calculate overall course progress
    total_lessons = sum(len(m["lessons"]) for m in modules_data)
    total_completed = sum(m["progress"]["completed_lessons"] for m in modules_data)
    overall_percentage = round(sum(m["progress"]["percentage"] for m in modules_data) / max(len(modules_data), 1), 2)
    
    return APIResponse.success({
        "student": {
            "id": student.id,
            "full_name": student.full_name,
            "created_at": student.created_at
        },
        "course": {
            "id": course_id,
            "progress": {
                "overall_percentage": overall_percentage,
                "completed_lessons": total_completed,
                "total_lessons": total_lessons
            }
        },
        "modules": modules_data,
        "summary": {
            "total_modules": len(modules_data),
            "total_lessons": total_lessons,
            "completed_lessons": total_completed,
            "total_words": sum(lesson["word_stats"]["total_words"] for module in modules_data for lesson in module["lessons"]),
            "weak_words": sum(lesson["word_stats"]["weak_words_count"] for module in modules_data for lesson in module["lessons"]),
            "practiced_words": sum(lesson["word_stats"]["practiced_words"] for module in modules_data for lesson in module["lessons"]),
            "mastered_words": sum(lesson["word_stats"]["mastered_words"] for module in modules_data for lesson in module["lessons"])
        }
    })


@router.patch("/password")
def change_teacher_password(
        password_data: schemas.TeacherPasswordChangeRequest,
        current_user: dict = Depends(get_teacher_user),
        db: Session = Depends(get_db)
):
    """Change teacher password"""
    # Validate password confirmation
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")
    
    # Get current teacher user
    teacher_user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not teacher_user:
        raise HTTPException(status_code=404, detail="Teacher user not found")
    
    # Verify current password
    from ..utils import verify_password
    if not verify_password(password_data.current_password, teacher_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Update password
    from ..utils import hash_password
    teacher_user.password_hash = hash_password(password_data.new_password)
    db.commit()
    
    return APIResponse.success({"message": "Password updated successfully"})
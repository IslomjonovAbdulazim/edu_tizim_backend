from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ..database import get_db
from ..models import *
from ..services import LeaderboardService
from ..utils import APIResponse, check_center_active, get_current_user_data
from ..dependencies import get_current_user

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
                "total_coins": total_coins
            }
        }
        students_with_progress.append(student_data)

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

    # Get word progress for weak words
    weak_words = db.query(WordProgress).filter(
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
            "word_id": w.word_id,
            "last_seven_attempts": w.last_seven_attempts,
            "total_correct": w.total_correct,
            "total_attempts": w.total_attempts
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
    active_students = db.query(Progress.profile_id).join(GroupMember).filter(
        GroupMember.group_id.in_(group_ids),
        Progress.last_practiced >= week_ago
    ).distinct().count() if group_ids else 0

    # Average completion rate
    all_progress = []
    if group_ids:
        all_progress = db.query(Progress).join(LearningCenterProfile).join(
            GroupMember
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
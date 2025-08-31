from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import *
from ..services import LeaderboardService
from ..utils import APIResponse, check_center_active

router = APIRouter()


@router.get("/dashboard")
def teacher_dashboard(db: Session = Depends(get_db)):
    """Teacher dashboard with assigned groups overview"""
    profile_id = 1  # Get from auth

    profile = db.query(LearningCenterProfile).filter(
        LearningCenterProfile.id == profile_id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    check_center_active(profile.center_id, db)

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

    # Get recent progress
    recent_progress = db.query(Progress).join(LearningCenterProfile).join(
        GroupMember
    ).join(Group).filter(
        Group.teacher_id == profile_id,
        Group.is_active == True
    ).order_by(Progress.last_practiced.desc()).limit(10).all()

    return APIResponse.success({
        "profile": profile,
        "stats": {
            "assigned_groups": len(assigned_groups),
            "total_students": total_students
        },
        "groups": assigned_groups,
        "recent_activity": recent_progress
    })


@router.get("/groups")
def get_my_groups(db: Session = Depends(get_db)):
    """Get groups assigned to teacher"""
    profile_id = 1  # Get from auth

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
def get_group_students(group_id: int, db: Session = Depends(get_db)):
    """Get students in a specific group"""
    profile_id = 1  # Get from auth

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
            "profile": student,
            "progress": {
                "completed_lessons": completed_lessons,
                "total_lessons": len(total_progress),
                "average_percentage": round(avg_percentage, 2),
                "total_coins": total_coins
            }
        }
        students_with_progress.append(student_data)

    return APIResponse.success(students_with_progress)


@router.get("/students/{student_id}/progress")
def get_student_progress(student_id: int, db: Session = Depends(get_db)):
    """Get detailed progress for a specific student"""
    profile_id = 1  # Get from auth

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
        "student": student,
        "progress": progress_records,
        "weak_words": weak_words,
        "recent_activity": recent_coins
    })


@router.get("/groups/{group_id}/leaderboard")
def get_group_leaderboard(group_id: int, db: Session = Depends(get_db)):
    """Get leaderboard for specific group"""
    profile_id = 1  # Get from auth

    # Check if teacher is assigned to this group
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.teacher_id == profile_id
    ).first()

    if not group:
        raise HTTPException(status_code=403, detail="Not authorized for this group")

    leaderboard = LeaderboardService.get_group_leaderboard(db, group_id)

    return APIResponse.success(leaderboard)


@router.get("/analytics/overview")
def get_teacher_analytics(db: Session = Depends(get_db)):
    """Get analytics overview for teacher's groups"""
    profile_id = 1  # Get from auth

    # Get all assigned groups
    groups = db.query(Group).filter(
        Group.teacher_id == profile_id,
        Group.is_active == True
    ).all()

    group_ids = [g.id for g in groups]

    # Total students across all groups
    total_students = db.query(GroupMember).filter(
        GroupMember.group_id.in_(group_ids)
    ).count()

    # Active students (those who practiced in last 7 days)
    from datetime import datetime, timedelta
    week_ago = datetime.now() - timedelta(days=7)

    active_students = db.query(Progress.profile_id).join(GroupMember).filter(
        GroupMember.group_id.in_(group_ids),
        Progress.last_practiced >= week_ago
    ).distinct().count()

    # Average completion rate
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
def get_struggling_students(db: Session = Depends(get_db)):
    """Get students who need attention (low progress/activity)"""
    profile_id = 1  # Get from auth

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
                "student": student,
                "reason": "No progress recorded",
                "avg_percentage": 0
            })
            continue

        avg_percentage = sum(p.percentage for p in progress_records) / len(progress_records)

        # Students with less than 50% average or no activity in last 3 days
        if avg_percentage < 50:
            struggling_students.append({
                "student": student,
                "reason": "Low completion rate",
                "avg_percentage": round(avg_percentage, 2)
            })

        # Check for inactivity
        from datetime import datetime, timedelta
        three_days_ago = datetime.now() - timedelta(days=3)

        recent_activity = any(p.last_practiced >= three_days_ago for p in progress_records)

        if not recent_activity:
            struggling_students.append({
                "student": student,
                "reason": "No recent activity",
                "avg_percentage": round(avg_percentage, 2)
            })

    return APIResponse.success(struggling_students)


@router.get("/content/courses")
def get_assigned_courses(db: Session = Depends(get_db)):
    """Get courses assigned to teacher's groups"""
    profile_id = 1  # Get from auth

    courses = db.query(Course).join(Group).filter(
        Group.teacher_id == profile_id,
        Group.is_active == True,
        Course.is_active == True
    ).distinct().all()

    return APIResponse.success(courses)


@router.get("/reports/weekly")
def get_weekly_report(db: Session = Depends(get_db)):
    """Get weekly activity report for teacher's groups"""
    profile_id = 1  # Get from auth

    from datetime import datetime, timedelta
    week_ago = datetime.now() - timedelta(days=7)

    # Get progress in last week
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
            "daily_breakdown": list(daily_activity.values())
        }
    })
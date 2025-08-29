from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.badge_service import BadgeService
from app.schemas.badge import (
    BadgeResponse,
    MarkBadgeAsSeenRequest,
    MarkBadgesAsSeenRequest,
    MarkAllBadgesAsSeenRequest,
    BadgeNotificationResponse,
    BadgeNotificationSummary
)
from app.schemas.common import SuccessResponse
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter()
badge_service = BadgeService()


@router.get("/notifications/{user_id}", response_model=BadgeNotificationResponse)
async def get_badge_notifications(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get badge notifications for user - shows unseen badges"""

    # Authorization check (users can only see their own notifications)
    if current_user.id != user_id and not current_user.has_any_role(["admin", "ceo"]):
        raise HTTPException(status_code=403, detail="Access denied")

    notifications = badge_service.get_badge_notifications(db, user_id)

    return BadgeNotificationResponse(
        unseen_badges_count=notifications["unseen_badges_count"],
        has_new_badges=notifications["has_new_badges"],
        unseen_badges=[BadgeResponse.from_orm(badge) for badge in notifications["unseen_badges"]]
    )


@router.post("/mark-seen", response_model=SuccessResponse)
async def mark_badge_as_seen(
        request: MarkBadgeAsSeenRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Mark a single badge as seen"""

    result = badge_service.mark_badge_as_seen(db, request.badge_id, current_user.id)

    return SuccessResponse(
        success=result["success"],
        message=result["message"],
        data={
            "badge_id": result["badge_id"],
            "seen_at": result.get("seen_at"),
            "was_already_seen": result["was_already_seen"]
        }
    )


@router.post("/mark-multiple-seen", response_model=SuccessResponse)
async def mark_multiple_badges_as_seen(
        request: MarkBadgesAsSeenRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Mark multiple badges as seen"""

    result = badge_service.mark_badges_as_seen(db, request.badge_ids, current_user.id)

    return SuccessResponse(
        success=result["success"],
        message=result["message"],
        data={
            "marked_as_seen": result["marked_as_seen"],
            "already_seen": result["already_seen"],
            "total_processed": len(request.badge_ids)
        }
    )


@router.post("/mark-all-seen", response_model=SuccessResponse)
async def mark_all_badges_as_seen(
        request: MarkAllBadgesAsSeenRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Mark ALL unseen badges as seen for a user"""

    # Authorization check
    if current_user.id != request.user_id and not current_user.has_any_role(["admin", "ceo"]):
        raise HTTPException(status_code=403, detail="Access denied")

    result = badge_service.mark_all_badges_as_seen(db, request.user_id)

    return SuccessResponse(
        success=result["success"],
        message=result["message"],
        data={"marked_count": result["marked_count"]}
    )


@router.get("/summary/{user_id}", response_model=dict)
async def get_user_badge_summary(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get comprehensive badge summary for user dashboard"""

    # Authorization check
    if current_user.id != user_id and not current_user.has_any_role(["admin", "ceo"]):
        raise HTTPException(status_code=403, detail="Access denied")

    summary = badge_service.get_user_badge_summary(db, user_id)
    return summary


@router.get("/unseen/{user_id}", response_model=List[BadgeResponse])
async def get_unseen_badges(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get list of all unseen badges for user"""

    # Authorization check
    if current_user.id != user_id and not current_user.has_any_role(["admin", "ceo"]):
        raise HTTPException(status_code=403, detail="Access denied")

    unseen_badges = badge_service.get_unseen_badges(db, user_id)
    return [BadgeResponse.from_orm(badge) for badge in unseen_badges]


@router.get("/notification-summary/{user_id}", response_model=BadgeNotificationSummary)
async def get_notification_summary(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get quick notification summary for user (for header/navbar display)"""

    # Authorization check
    if current_user.id != user_id and not current_user.has_any_role(["admin", "ceo"]):
        raise HTTPException(status_code=403, detail="Access denied")

    from app.repositories.badge_repository import BadgeRepository
    badge_repo = BadgeRepository()

    summary = badge_repo.get_notification_summary(db, user_id)

    return BadgeNotificationSummary(
        user_id=user_id,
        total_badges=summary["total_badges"],
        unseen_badges=summary["unseen_badges"],
        new_achievements=summary["recent_badges_24h"],
        recent_level_ups=0  # Could be calculated if needed
    )


@router.get("/user/{user_id}", response_model=List[BadgeResponse])
async def get_user_badges(
        user_id: int,
        include_unseen_only: bool = Query(False, description="Only return unseen badges"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get all badges for a user with optional filtering"""

    # Authorization check
    if current_user.id != user_id and not current_user.has_any_role(["admin", "ceo"]):
        raise HTTPException(status_code=403, detail="Access denied")

    from app.repositories.badge_repository import BadgeRepository
    badge_repo = BadgeRepository()

    if include_unseen_only:
        badges = badge_repo.get_unseen_badges(db, user_id)
    else:
        badges = badge_repo.get_user_badges(db, user_id)

    return [BadgeResponse.from_orm(badge) for badge in badges]


# Admin endpoints
@router.post("/admin/reset-notifications/{user_id}", response_model=SuccessResponse)
async def reset_user_badge_notifications(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Admin: Reset all badge notifications for a user (mark all as unseen)"""

    # Admin only
    if not current_user.has_any_role(["admin", "ceo"]):
        raise HTTPException(status_code=403, detail="Admin access required")

    result = badge_service.reset_badge_notifications(db, user_id)

    return SuccessResponse(
        success=result["success"],
        message=result["message"],
        data={"updated_count": result["updated_count"]}
    )
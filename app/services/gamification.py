from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import date, timedelta
from app.models import UserRole, LeaderboardType, BadgeCategory, User, Progress, LeaderboardEntry, UserBadge
from app.schemas import (
    LeaderboardEntryResponse, LeaderboardQuery, LeaderboardResponse,
    UserBadgeResponse, BadgeProgress, UserBadgesSummary, GameStats
)
from app.services.base import BaseService


class GamificationService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)

    # Leaderboard Management
    def get_leaderboard(self, query: LeaderboardQuery, requester_id: int) -> Dict[str, Any]:
        """Get leaderboard entries"""
        requester = self.repos.user.get(requester_id)
        if not requester:
            return self._format_error_response("User not found")

        # Permission check for group leaderboards
        if query.leaderboard_type in [LeaderboardType.GROUP_3_DAILY, LeaderboardType.GROUP_ALL_TIME]:
            if not query.group_id:
                return self._format_error_response("Group ID required for group leaderboards")

            # Check if user is in the group or has permissions to view
            group = self.repos.group.get(query.group_id)
            if not group:
                return self._format_error_response("Group not found")

            # Check permissions
            can_view_group = (
                    requester.has_role(UserRole.SUPER_ADMIN) or
                    (requester.learning_center_id == group.branch.learning_center_id and
                     requester.has_any_role([UserRole.ADMIN, UserRole.TEACHER, UserRole.GROUP_MANAGER])) or
                    (requester.id in [s.id for s in group.students])  # Student in the group
            )

            if not can_view_group:
                return self._format_error_response("Insufficient permissions to view this group leaderboard")

        # Get leaderboard entries
        entries = self.repos.leaderboard.get_leaderboard(
            query.leaderboard_type,
            query.group_id,
            query.leaderboard_date,
            query.limit
        )

        # Get user's rank in this leaderboard
        user_rank_entry = self.repos.leaderboard.get_user_rank(
            requester_id,
            query.leaderboard_type,
            query.group_id,
            query.leaderboard_date
        )

        user_rank = user_rank_entry.rank if user_rank_entry else None

        entries_data = [LeaderboardEntryResponse.from_orm(entry) for entry in entries]

        response = LeaderboardResponse(
            leaderboard_type=query.leaderboard_type,
            group_id=query.group_id,
            leaderboard_date=query.leaderboard_date,
            entries=entries_data,
            user_rank=user_rank
        )

        return self._format_success_response(response)

    def update_leaderboards(self, learning_center_id: Optional[int] = None) -> Dict[str, Any]:
        """Update all leaderboards (scheduled job)"""
        # This is typically called by a background job

        try:
            results = {}

            # Update 3-daily global leaderboard
            self._update_3_daily_global_leaderboard()
            results["3_daily_global"] = "updated"

            # Update all-time global leaderboard
            self._update_all_time_global_leaderboard()
            results["all_time_global"] = "updated"

            # Update group leaderboards
            if learning_center_id:
                groups = self.repos.group.get_groups_by_learning_center(learning_center_id)
            else:
                # Get all active groups (super admin operation)
                from app.models import Group
                groups = self.db.query(Group).filter(Group.is_active == True).all()

            for group in groups:
                self._update_group_leaderboards(group.id)

            results["group_leaderboards"] = f"updated {len(groups)} groups"

            return self._format_success_response(results, "Leaderboards updated successfully")

        except Exception as e:
            return self._format_error_response(f"Failed to update leaderboards: {str(e)}")

    def _update_3_daily_global_leaderboard(self) -> None:
        """Update 3-daily global leaderboard"""
        # Get all users and their points from last 3 days
        cutoff_date = date.today() - timedelta(days=3)

        # This is a simplified implementation
        # You'll need to calculate points from the last 3 days properly
        user_rankings = []

        # Get all users with recent activity
        from app.models import User, Progress
        users_with_points = self.db.query(User, func.sum(Progress.points)).join(Progress).filter(
            Progress.updated_at >= cutoff_date
        ).group_by(User.id).order_by(func.sum(Progress.points).desc()).all()

        for user, points in users_with_points:
            user_rankings.append({
                "user_id": user.id,
                "points": int(points) if points else 0,
                "user_full_name": user.full_name
            })

        # Update leaderboard
        self.repos.leaderboard.update_leaderboard(
            LeaderboardType.GLOBAL_3_DAILY,
            user_rankings,
            leaderboard_date=date.today()
        )

    def _update_all_time_global_leaderboard(self) -> None:
        """Update all-time global leaderboard"""
        # Get all users and their total points
        from app.models import User, Progress
        users_with_points = self.db.query(User, func.sum(Progress.points)).join(Progress).group_by(User.id).order_by(
            func.sum(Progress.points).desc()).all()

        user_rankings = []
        for user, points in users_with_points:
            user_rankings.append({
                "user_id": user.id,
                "points": int(points) if points else 0,
                "user_full_name": user.full_name
            })

        # Update leaderboard
        self.repos.leaderboard.update_leaderboard(
            LeaderboardType.GLOBAL_ALL_TIME,
            user_rankings
        )

    def _update_group_leaderboards(self, group_id: int) -> None:
        """Update both 3-daily and all-time leaderboards for a group"""
        group = self.repos.group.get_with_students(group_id)
        if not group:
            return

        student_ids = [student.id for student in group.students]
        if not student_ids:
            return

        # 3-daily group leaderboard
        cutoff_date = date.today() - timedelta(days=3)

        from app.models import Progress
        students_3_daily = self.db.query(User, func.sum(Progress.points)).join(Progress).filter(
            and_(
                User.id.in_(student_ids),
                Progress.updated_at >= cutoff_date
            )
        ).group_by(User.id).order_by(func.sum(Progress.points).desc()).all()

        rankings_3_daily = []
        for user, points in students_3_daily:
            rankings_3_daily.append({
                "user_id": user.id,
                "points": int(points) if points else 0,
                "user_full_name": user.full_name
            })

        if rankings_3_daily:
            self.repos.leaderboard.update_leaderboard(
                LeaderboardType.GROUP_3_DAILY,
                rankings_3_daily,
                group_id=group_id,
                leaderboard_date=date.today()
            )

        # All-time group leaderboard
        students_all_time = self.db.query(User, func.sum(Progress.points)).join(Progress).filter(
            User.id.in_(student_ids)
        ).group_by(User.id).order_by(func.sum(Progress.points).desc()).all()

        rankings_all_time = []
        for user, points in students_all_time:
            rankings_all_time.append({
                "user_id": user.id,
                "points": int(points) if points else 0,
                "user_full_name": user.full_name
            })

        if rankings_all_time:
            self.repos.leaderboard.update_leaderboard(
                LeaderboardType.GROUP_ALL_TIME,
                rankings_all_time,
                group_id=group_id
            )

    # Badge Management
    def check_and_award_badges(self, user_id: int) -> Dict[str, Any]:
        """Check user achievements and award badges"""
        user = self.repos.user.get(user_id)
        if not user:
            return self._format_error_response("User not found")

        # Get user stats for badge calculations
        stats = self._get_user_badge_stats(user_id)

        # Check and award badges
        awarded_badges = self.repos.badge.check_and_award_badges(user_id, stats)

        if awarded_badges:
            badges_data = [UserBadgeResponse.from_orm(badge) for badge in awarded_badges]
            return self._format_success_response({
                "awarded_badges": badges_data,
                "count": len(awarded_badges)
            }, f"Awarded {len(awarded_badges)} badge(s)")

        return self._format_success_response([], "No new badges awarded")

    def _get_user_badge_stats(self, user_id: int) -> Dict[str, int]:
        """Get user statistics for badge calculation"""
        # Get daily first finishes
        daily_first_finishes = self.repos.leaderboard.get_daily_first_finishes_count(user_id)

        # Get perfect lessons (100% completion)
        perfect_lessons = self.repos.progress.get_perfect_lessons_count(user_id)

        # Get weaklist solved (mastered words)
        weaklist_solved = self.repos.weak_word.get_mastered_words_count(user_id)

        # Get position improvements
        position_improvements = self.repos.leaderboard.get_position_improvements_count(user_id)

        return {
            "daily_first_finishes": daily_first_finishes,
            "perfect_lessons": perfect_lessons,
            "weaklist_solved": weaklist_solved,
            "position_improvements": position_improvements
        }

    def get_user_badges(self, user_id: int, requester_id: int) -> Dict[str, Any]:
        """Get user's badges with progress"""
        # Permission check
        if user_id != requester_id:
            requester = self.repos.user.get(requester_id)
            user = self.repos.user.get(user_id)

            if not requester or not user:
                return self._format_error_response("User not found")

            can_view = (
                    requester.has_role(UserRole.SUPER_ADMIN) or
                    (requester.learning_center_id == user.learning_center_id and
                     requester.has_any_role([UserRole.ADMIN, UserRole.TEACHER]))
            )

            if not can_view:
                return self._format_error_response("Insufficient permissions")

        # Get user badges
        badges = self.repos.badge.get_user_badges(user_id)
        badges_data = [UserBadgeResponse.from_orm(badge) for badge in badges]

        # Get badge progress
        badge_progress = self.repos.badge.get_badge_progress(user_id)

        summary = UserBadgesSummary(
            user_id=user_id,
            badges=badges_data,
            badge_progress=badge_progress,
            total_badges=len(badges_data)
        )

        return self._format_success_response(summary)

    def get_badge_leaderboard(self, learning_center_id: int, requester_id: int) -> Dict[str, Any]:
        """Get badge leaderboard (users with most badges)"""
        if not self._check_permissions(requester_id, [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.TEACHER],
                                       learning_center_id):
            return self._format_error_response("Insufficient permissions")

        # Get users with badge counts
        from app.models import User, UserBadge
        users_with_badges = self.db.query(
            User, func.count(UserBadge.id)
        ).outerjoin(UserBadge).filter(
            and_(
                User.learning_center_id == learning_center_id,
                User.is_active == True
            )
        ).group_by(User.id).order_by(func.count(UserBadge.id).desc()).limit(50).all()

        leaderboard = []
        for i, (user, badge_count) in enumerate(users_with_badges, 1):
            leaderboard.append({
                "rank": i,
                "user_id": user.id,
                "user_full_name": user.full_name,
                "badge_count": badge_count,
                "total_points": user.total_points
            })

        return self._format_success_response(leaderboard)

    # Game Statistics
    def get_user_game_stats(self, user_id: int, requester_id: int) -> Dict[str, Any]:
        """Get comprehensive game statistics for user"""
        # Permission check
        if user_id != requester_id:
            if not self._check_permissions(requester_id, [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.TEACHER]):
                return self._format_error_response("Insufficient permissions")

        user = self.repos.user.get(user_id)
        if not user:
            return self._format_error_response("User not found")

        # Get current ranks
        global_rank_entry = self.repos.leaderboard.get_user_rank(user_id, LeaderboardType.GLOBAL_ALL_TIME)
        current_rank_global = global_rank_entry.rank if global_rank_entry else None

        # Get group rank (first group they're in)
        user_groups = self.repos.group.get_student_groups(user_id)
        current_rank_group = None
        if user_groups:
            group_rank_entry = self.repos.leaderboard.get_user_rank(
                user_id, LeaderboardType.GROUP_ALL_TIME, group_id=user_groups[0].id
            )
            current_rank_group = group_rank_entry.rank if group_rank_entry else None

        # Get badge and achievement stats
        badge_stats = self._get_user_badge_stats(user_id)
        badges_earned = self.repos.badge.get_total_badges_count(user_id)

        stats = GameStats(
            user_id=user_id,
            total_points=user.total_points,
            current_rank_global=current_rank_global,
            current_rank_group=current_rank_group,
            badges_earned=badges_earned,
            position_improvements=badge_stats["position_improvements"],
            perfect_lessons=badge_stats["perfect_lessons"],
            daily_first_finishes=badge_stats["daily_first_finishes"],
            weaklist_completions=badge_stats["weaklist_solved"]
        )

        return self._format_success_response(stats)

    def trigger_leaderboard_badges(self, leaderboard_date: Optional[date] = None) -> Dict[str, Any]:
        """Trigger badge awards based on leaderboard positions (daily job)"""
        if not leaderboard_date:
            leaderboard_date = date.today()

        awarded_count = 0

        # Get top performers from 3-daily leaderboards
        global_entries = self.repos.leaderboard.get_leaderboard(
            LeaderboardType.GLOBAL_3_DAILY,
            leaderboard_date=leaderboard_date,
            limit=10
        )

        # Award badges for top 3 global performers
        for entry in global_entries[:3]:
            if entry.rank == 1:
                # Award daily first place badge
                awarded_badges = self.repos.badge.check_and_award_badges(
                    entry.user_id,
                    {"daily_first_finishes": self.repos.leaderboard.get_daily_first_finishes_count(entry.user_id)}
                )
                awarded_count += len(awarded_badges)

        return self._format_success_response({
            "badges_awarded": awarded_count,
            "date": leaderboard_date
        }, f"Awarded {awarded_count} leaderboard badges")

    def get_gamification_overview(self, learning_center_id: int, requester_id: int) -> Dict[str, Any]:
        """Get gamification overview for learning center"""
        if not self._check_permissions(requester_id, [UserRole.ADMIN, UserRole.SUPER_ADMIN], learning_center_id):
            return self._format_error_response("Admin access required")

        # Get active users count
        users = self.repos.user.get_active_users_by_center(learning_center_id)
        active_users_count = len(users)

        # Get total points in center
        total_points = sum(user.total_points for user in users)

        # Get total badges awarded
        from app.models import UserBadge, User
        total_badges = self.db.query(UserBadge).join(User).filter(
            User.learning_center_id == learning_center_id
        ).count()

        # Get leaderboard participation
        today = date.today()
        daily_participants = self.db.query(LeaderboardEntry).join(User).filter(
            and_(
                User.learning_center_id == learning_center_id,
                LeaderboardEntry.leaderboard_type == LeaderboardType.GLOBAL_3_DAILY,
                LeaderboardEntry.leaderboard_date == today
            )
        ).count()

        overview = {
            "active_users": active_users_count,
            "total_points": total_points,
            "total_badges": total_badges,
            "daily_participants": daily_participants,
            "participation_rate": (daily_participants / active_users_count * 100) if active_users_count > 0 else 0
        }

        return self._format_success_response(overview)
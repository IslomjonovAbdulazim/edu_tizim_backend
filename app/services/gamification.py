from __future__ import annotations
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.models.gamification import LeaderboardEntry, LeaderboardType
from app.repositories.base import BaseRepository
from .base import BaseService


class GamificationService(BaseService[LeaderboardEntry]):
    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = BaseRepository[LeaderboardEntry](db, LeaderboardEntry)

    def add_points(self, user_id: int, points: int, *, type_: LeaderboardType = LeaderboardType.WEEKLY) -> LeaderboardEntry:
        with self.transaction():
            entry = self.repo.create({"user_id": user_id, "points": points, "type": type_})
        return entry

    def get_leaderboard(self, type_: LeaderboardType = LeaderboardType.WEEKLY, *, limit: int = 50) -> List[LeaderboardEntry]:
        return (
            self.db.query(LeaderboardEntry)
            .filter(and_(LeaderboardEntry.type == type_, LeaderboardEntry.is_active.is_(True)))
            .order_by(desc(LeaderboardEntry.points))
            .limit(limit)
            .all()
        )

    def get_user_rank(self, user_id: int, type_: LeaderboardType = LeaderboardType.WEEKLY) -> Optional[int]:
        # naive approach; consider window functions if needed
        entries = (
            self.db.query(LeaderboardEntry.user_id, LeaderboardEntry.points)
            .filter(and_(LeaderboardEntry.type == type_, LeaderboardEntry.is_active.is_(True)))
            .order_by(desc(LeaderboardEntry.points))
            .all()
        )
        for idx, (uid, _) in enumerate(entries, start=1):
            if uid == user_id:
                return idx
        return None

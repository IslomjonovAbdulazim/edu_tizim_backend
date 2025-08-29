from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.models.base import BaseModel


class Notification(BaseModel):
    """System notification model - for sending notifications to users"""
    __tablename__ = "notifications"

    # Target user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Notification content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), nullable=False)  # badge, achievement, reminder, system, leaderboard
    priority = Column(String(20), default="normal")  # low, normal, high, urgent

    # Rich content
    icon = Column(String(200), nullable=True)  # Icon URL or name
    image_url = Column(String(500), nullable=True)  # Optional image
    action_url = Column(String(500), nullable=True)  # Link to specific page/feature
    action_text = Column(String(100), nullable=True)  # Button text like "View Badge"

    # Metadata
    metadata = Column(JSON, nullable=True)  # Additional context data
    # Example: {"badge_id": 123, "leaderboard_rank": 5, "points_earned": 50}

    # Status tracking
    is_read = Column(Boolean, default=False)
    is_sent = Column(Boolean, default=False)  # For push notifications
    read_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # Auto-expire old notifications

    # Delivery channels
    show_in_app = Column(Boolean, default=True)
    send_push = Column(Boolean, default=False)
    send_email = Column(Boolean, default=False)
    send_telegram = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="notifications")

    def __str__(self):
        return f"Notification({self.user_id}, {self.type}, {self.title})"

    @property
    def is_expired(self):
        """Check if notification has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_urgent(self):
        """Check if notification is urgent"""
        return self.priority == "urgent"

    @property
    def is_high_priority(self):
        """Check if notification is high priority or above"""
        return self.priority in ["high", "urgent"]

    @property
    def age_hours(self):
        """Get notification age in hours"""
        return (datetime.utcnow() - self.created_at).total_seconds() / 3600

    @property
    def is_recent(self):
        """Check if notification is recent (less than 24 hours)"""
        return self.age_hours < 24

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()

    def mark_as_sent(self):
        """Mark notification as sent"""
        if not self.is_sent:
            self.is_sent = True
            self.sent_at = datetime.utcnow()

    def set_expiry(self, days: int):
        """Set expiry date"""
        self.expires_at = datetime.utcnow() + timedelta(days=days)

    def get_metadata_value(self, key: str, default=None):
        """Get value from metadata"""
        if not self.metadata:
            return default
        return self.metadata.get(key, default)

    @classmethod
    def create_badge_notification(
            cls,
            user_id: int,
            badge_name: str,
            badge_icon: str = None,
            badge_id: int = None
    ):
        """Factory method for badge notifications"""
        return cls(
            user_id=user_id,
            title="🏆 Badge Earned!",
            message=f"Congratulations! You've earned the '{badge_name}' badge!",
            type="badge",
            priority="normal",
            icon=badge_icon or "trophy",
            action_text="View Badge",
            show_in_app=True,
            send_push=True,
            metadata={"badge_id": badge_id, "badge_name": badge_name}
        )

    @classmethod
    def create_leaderboard_notification(
            cls,
            user_id: int,
            rank: int,
            leaderboard_type: str = "daily",
            points: int = 0
    ):
        """Factory method for leaderboard notifications"""
        if rank == 1:
            title = "🥇 First Place!"
            message = f"Amazing! You're #1 on the {leaderboard_type} leaderboard with {points} points!"
            priority = "high"
        elif rank <= 3:
            title = "🥉 Top 3!"
            message = f"Great job! You're #{rank} on the {leaderboard_type} leaderboard with {points} points!"
            priority = "normal"
        elif rank <= 10:
            title = "⭐ Top 10!"
            message = f"Well done! You're #{rank} on the {leaderboard_type} leaderboard with {points} points!"
            priority = "normal"
        else:
            title = "📈 Leaderboard Update"
            message = f"You're #{rank} on the {leaderboard_type} leaderboard with {points} points!"
            priority = "low"

        return cls(
            user_id=user_id,
            title=title,
            message=message,
            type="leaderboard",
            priority=priority,
            icon="trophy",
            action_text="View Leaderboard",
            show_in_app=True,
            send_push=rank <= 10,  # Only push for top 10
            metadata={
                "rank": rank,
                "leaderboard_type": leaderboard_type,
                "points": points
            }
        )

    @classmethod
    def create_achievement_notification(
            cls,
            user_id: int,
            achievement_name: str,
            achievement_description: str,
            points_earned: int = 0
    ):
        """Factory method for achievement notifications"""
        return cls(
            user_id=user_id,
            title="🎯 Achievement Unlocked!",
            message=f"You've unlocked '{achievement_name}': {achievement_description}",
            type="achievement",
            priority="normal",
            icon="star",
            action_text="View Achievements",
            show_in_app=True,
            send_push=True,
            metadata={
                "achievement_name": achievement_name,
                "points_earned": points_earned
            }
        )

    @classmethod
    def create_reminder_notification(
            cls,
            user_id: int,
            reminder_type: str,
            custom_message: str = None
    ):
        """Factory method for reminder notifications"""
        messages = {
            "daily_practice": "Don't forget your daily practice! Keep your streak alive! 🔥",
            "weak_words": "Time to review your weak words and strengthen your vocabulary! 📚",
            "lesson_incomplete": "You have incomplete lessons waiting. Let's finish what you started! 📖",
            "group_activity": "Your study group is active! Join your classmates in learning! 👥"
        }

        message = custom_message or messages.get(reminder_type, "Don't forget to practice!")

        return cls(
            user_id=user_id,
            title="📚 Learning Reminder",
            message=message,
            type="reminder",
            priority="low",
            icon="bell",
            action_text="Continue Learning",
            show_in_app=True,
            send_push=True,
            metadata={"reminder_type": reminder_type}
        )

    @classmethod
    def create_system_notification(
            cls,
            user_id: int,
            title: str,
            message: str,
            priority: str = "normal"
    ):
        """Factory method for system notifications"""
        return cls(
            user_id=user_id,
            title=title,
            message=message,
            type="system",
            priority=priority,
            icon="info",
            show_in_app=True,
            send_push=priority in ["high", "urgent"]
        )

    def to_dict(self):
        """Convert to dictionary"""
        data = super().to_dict()
        data.update({
            'is_expired': self.is_expired,
            'is_urgent': self.is_urgent,
            'is_high_priority': self.is_high_priority,
            'age_hours': self.age_hours,
            'is_recent': self.is_recent
        })
        return data
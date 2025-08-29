from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Time, Text
from sqlalchemy.orm import relationship
from datetime import date
from app.models.base import BaseModel
from app.models.student import student_groups


class Group(BaseModel):
    __tablename__ = "groups"

    # Basic info
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)

    # Schedule
    schedule_days = Column(String(20))  # "Mon,Wed,Fri"
    start_time = Column(Time)
    end_time = Column(Time)

    # Relationships
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"))

    # Related objects
    learning_center = relationship("LearningCenter")
    branch = relationship("Branch", back_populates="groups")
    course = relationship("Course", back_populates="groups")
    teacher = relationship("Teacher", back_populates="groups")
    students = relationship("Student", secondary=student_groups, back_populates="groups")

    # Leaderboard relationships
    leaderboard_entries = relationship("GroupLeaderboard", back_populates="group", cascade="all, delete-orphan")

    def __str__(self):
        teacher_name = self.teacher.full_name if self.teacher else "No teacher"
        return f"Group({self.name}, {self.course.name}, {teacher_name})"

    @property
    def current_capacity(self):
        return len(self.students)

    @property
    def students_count(self):
        return len(self.students)

    @property
    def max_capacity(self):
        """Maximum capacity - could be defined per group or use default"""
        # You might want to add a max_capacity column to groups table
        return 25  # Default max capacity

    @property
    def available_spots(self):
        """Available spots in the group"""
        return max(0, self.max_capacity - self.current_capacity)

    @property
    def is_full(self):
        """Check if group is at capacity"""
        return self.current_capacity >= self.max_capacity

    @property
    def capacity_percentage(self):
        """Capacity utilization percentage"""
        if self.max_capacity == 0:
            return 0
        return (self.current_capacity / self.max_capacity) * 100

    def get_daily_leaderboard(self, target_date: date = None):
        """Get daily leaderboard for this group"""
        if target_date is None:
            target_date = date.today()

        daily_entries = [
            entry for entry in self.leaderboard_entries
            if entry.is_daily and entry.leaderboard_date == target_date
        ]

        # Sort by rank
        return sorted(daily_entries, key=lambda x: x.rank)

    def get_all_time_leaderboard(self):
        """Get all-time leaderboard for this group"""
        all_time_entries = [
            entry for entry in self.leaderboard_entries
            if entry.is_all_time
        ]

        # Sort by rank
        return sorted(all_time_entries, key=lambda x: x.rank)

    def get_leaderboard_stats(self, target_date: date = None):
        """Get leaderboard statistics for this group"""
        if target_date is None:
            target_date = date.today()

        daily_leaderboard = self.get_daily_leaderboard(target_date)
        all_time_leaderboard = self.get_all_time_leaderboard()

        return {
            'group_id': self.id,
            'group_name': self.name,
            'daily': {
                'date': target_date,
                'participants': len(daily_leaderboard),
                'top_performer': daily_leaderboard[0].user_full_name if daily_leaderboard else None,
                'top_points': daily_leaderboard[0].points if daily_leaderboard else 0
            },
            'all_time': {
                'participants': len(all_time_leaderboard),
                'top_performer': all_time_leaderboard[0].user_full_name if all_time_leaderboard else None,
                'top_points': all_time_leaderboard[0].points if all_time_leaderboard else 0
            }
        }
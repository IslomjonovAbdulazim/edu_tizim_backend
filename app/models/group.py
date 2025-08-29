from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Time, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.models.student import student_groups

class Group(BaseModel):
    __tablename__ = "groups"

    # Basic info
    name = Column(String(100), nullable=False)
    description = Column(Text)
    max_capacity = Column(Integer, default=20)
    is_active = Column(Boolean, default=True, nullable=False)

    # Schedule
    schedule_days = Column(String(20))  # "Mon,Wed,Fri"
    start_time = Column(Time)
    end_time = Column(Time)

    # Relationships
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"))

    # Related objects
    course = relationship("Course", back_populates="groups")
    teacher = relationship("Teacher", back_populates="groups")
    students = relationship("Student", secondary=student_groups, back_populates="groups")

    def __str__(self):
        teacher_name = self.teacher.full_name if self.teacher else "No teacher"
        return f"Group({self.name}, {self.course.name}, {teacher_name})"

    @property
    def current_capacity(self):
        return len(self.students)

    @property
    def available_spots(self):
        return self.max_capacity - self.current_capacity

    @property
    def is_full(self):
        return self.current_capacity >= self.max_capacity

    @property
    def capacity_percentage(self):
        return round((self.current_capacity / self.max_capacity) * 100, 1) if self.max_capacity > 0 else 0
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Time, Numeric, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Branch(BaseModel):
    __tablename__ = "branches"

    # Basic branch information
    name = Column(String(100), nullable=False)  # "Downtown Branch", "North Campus", etc.
    description = Column(Text, nullable=True)

    # Location information
    address = Column(String(500), nullable=False)
    latitude = Column(Numeric(10, 8), nullable=True)  # -90.00000000 to 90.00000000
    longitude = Column(Numeric(11, 8), nullable=True)  # -180.00000000 to 180.00000000

    # Contact information
    phone_number = Column(String(20), nullable=True)

    # Operational settings
    is_active = Column(Boolean, default=True, nullable=False)

    # Operating hours
    opening_time = Column(Time, nullable=True)
    closing_time = Column(Time, nullable=True)

    # Learning Center relationship
    learning_center_id = Column(Integer, ForeignKey("learning_centers.id"), nullable=False)
    learning_center = relationship("LearningCenter", back_populates="branches")

    # Relationships
    groups = relationship("Group", back_populates="branch", cascade="all, delete-orphan")
    users = relationship("User", back_populates="branch")  # Staff assigned to this branch

    def __str__(self):
        return f"Branch(name='{self.name}', center='{self.learning_center.name if self.learning_center else 'Unknown'}')"

    @property
    def full_address_with_coords(self):
        """Get full address with coordinates if available"""
        addr = self.address
        if self.latitude and self.longitude:
            addr += f" (Lat: {self.latitude}, Lng: {self.longitude})"
        return addr

    @property
    def total_groups(self):
        """Get total number of groups in this branch"""
        return len(self.groups)

    @property
    def active_groups(self):
        """Get number of active groups in this branch"""
        return len([group for group in self.groups if group.is_active])

    @property
    def total_students(self):
        """Get total number of students across all groups in this branch"""
        return sum(len(group.students) for group in self.groups if group.is_active)

    @property
    def coordinates(self):
        """Get coordinates as a dict"""
        if self.latitude and self.longitude:
            return {
                "latitude": float(self.latitude),
                "longitude": float(self.longitude)
            }
        return None

    def get_operating_hours(self):
        """Get operating hours as formatted string"""
        if self.opening_time and self.closing_time:
            return f"{self.opening_time.strftime('%H:%M')} - {self.closing_time.strftime('%H:%M')}"
        return "Not specified"
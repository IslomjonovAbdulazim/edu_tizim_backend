from sqlalchemy import Column, Integer, ForeignKey, Date, Boolean, Table
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

# Association table for weak words in weekly lists
weeklist_words = Table(
    'weeklist_words',
    BaseModel.metadata,
    Column('weeklist_id', Integer, ForeignKey('weeklists.id'), primary_key=True),
    Column('word_id', Integer, ForeignKey('words.id'), primary_key=True)
)

class WeekList(BaseModel):
    __tablename__ = "weeklists"

    # User and date
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_date = Column(Date, nullable=False)
    is_completed = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="weekly_lists")
    words = relationship("Word", secondary=weeklist_words)

    def __str__(self):
        return f"WeekList({self.user.full_name}, {self.created_date})"

    @property
    def total_words(self):
        return len(self.words)

    @property
    def completion_status(self):
        return "Completed" if self.is_completed else f"{self.total_words} words remaining"
"""
Quiz system Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# Teacher Requests
class CreateQuizRoomRequest(BaseModel):
    lesson_ids: List[int] = Field(..., description="List of lesson IDs to include words from")
    num_questions: int = Field(..., ge=1, le=100, description="Number of questions (1-100)")
    is_locked: bool = Field(False, description="Whether room is private (join by code only)")

class StartQuizRequest(BaseModel):
    room_code: str = Field(..., min_length=3, max_length=3, description="3-digit room code")

class NextQuestionRequest(BaseModel):
    room_code: str = Field(..., min_length=3, max_length=3, description="3-digit room code")

class SkipQuestionRequest(BaseModel):
    room_code: str = Field(..., min_length=3, max_length=3, description="3-digit room code")

# Student Requests
class JoinRoomRequest(BaseModel):
    room_code: str = Field(..., min_length=3, max_length=3, description="3-digit room code")

class SubmitAnswerRequest(BaseModel):
    room_code: str = Field(..., min_length=3, max_length=3, description="3-digit room code")
    answer_index: int = Field(..., ge=0, le=3, description="Selected answer index (0-3)")

# Response Models
class QuizQuestionResponse(BaseModel):
    word: str
    options: List[str]  # 4 options
    question_number: int
    total_questions: int
    time_limit: int  # seconds

class PlayerResponse(BaseModel):
    user_id: int
    name: str
    score: int
    is_connected: bool

class LeaderboardResponse(BaseModel):
    rank: int
    user_id: int
    name: str
    score: int
    is_connected: bool
    # Enhanced fields for question results
    points_added: Optional[int] = None
    previous_rank: Optional[int] = None
    position_change: Optional[int] = None
    change_indicator: Optional[str] = None  # "up", "down", "same", "new"
    change_text: Optional[str] = None  # "+2", "-1", "0", "NEW"

class QuizRoomResponse(BaseModel):
    code: str
    teacher_name: str
    players_count: int
    num_questions: int
    status: str
    is_locked: bool
    created_at: datetime

class QuestionResultResponse(BaseModel):
    question: QuizQuestionResponse
    correct_answer: str
    correct_index: int
    leaderboard: List[LeaderboardResponse]
    players_answered: int
    total_players: int

class FinalResultResponse(BaseModel):
    final_leaderboard: List[LeaderboardResponse]
    total_questions: int
    quiz_duration: str  # Human readable duration

# Socket Event Payloads
class SocketResponse(BaseModel):
    event: str
    data: dict
    room: Optional[str] = None

# Error Response
class QuizErrorResponse(BaseModel):
    error: str
    message: str
    code: Optional[str] = None
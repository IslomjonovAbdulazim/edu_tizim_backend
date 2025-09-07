"""
Quiz system models - In-memory data structures for real-time quiz
No database storage needed as per requirements
"""
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import random
import string

class QuizStatus(Enum):
    WAITING = "waiting"  # Room created, waiting for players
    STARTING = "starting"  # Teacher pressed start, countdown to first question
    IN_PROGRESS = "in_progress"  # Quiz is running
    QUESTION_ENDED = "question_ended"  # Current question ended, showing results
    FINISHED = "finished"  # Quiz completed

class Player:
    def __init__(self, user_id: int, name: str, socket_id: str):
        self.user_id = user_id
        self.name = name
        self.socket_id = socket_id
        self.score = 0
        self.answers = []  # List of answers for each question
        self.joined_at = datetime.now()
        self.is_connected = True

class QuizQuestion:
    def __init__(self, word_id: int, word: str, meaning: str, options: List[str], correct_answer: str):
        self.word_id = word_id
        self.word = word
        self.meaning = meaning
        self.options = options  # List of 4 options
        self.correct_answer = correct_answer
        self.correct_index = options.index(correct_answer)

class PlayerAnswer:
    def __init__(self, player_id: int, answer_index: int, answer_time: float):
        self.player_id = player_id
        self.answer_index = answer_index
        self.answer_time = answer_time  # Time taken in seconds
        self.is_correct = False
        self.points_earned = 0

class QuizRoom:
    def __init__(self, code: str, teacher_id: int, teacher_name: str, teacher_socket_id: str, 
                 lesson_ids: List[int], num_questions: int, is_locked: bool = False):
        self.code = code
        self.teacher_id = teacher_id
        self.teacher_name = teacher_name
        self.teacher_socket_id = teacher_socket_id
        self.lesson_ids = lesson_ids
        self.num_questions = num_questions
        self.is_locked = is_locked
        self.status = QuizStatus.WAITING
        self.created_at = datetime.now()
        
        # Game state
        self.players: Dict[int, Player] = {}  # user_id -> Player
        self.questions: List[QuizQuestion] = []
        self.current_question_index = 0
        self.question_start_time: Optional[datetime] = None
        self.question_answers: List[PlayerAnswer] = []
        
        # Leaderboard tracking
        self.previous_leaderboard: List[Dict] = []  # Store previous question's leaderboard
        
        # Settings
        self.question_time_limit = 20  # seconds
        
    def add_player(self, user_id: int, name: str, socket_id: str) -> bool:
        """Add a player to the room"""
        if user_id not in self.players and self.status == QuizStatus.WAITING:
            self.players[user_id] = Player(user_id, name, socket_id)
            return True
        return False
    
    def remove_player(self, user_id: int) -> bool:
        """Remove a player from the room"""
        if user_id in self.players:
            del self.players[user_id]
            return True
        return False
    
    def get_current_question(self) -> Optional[QuizQuestion]:
        """Get the current question"""
        if 0 <= self.current_question_index < len(self.questions):
            return self.questions[self.current_question_index]
        return None
    
    def start_question(self):
        """Start the current question timer"""
        self.question_start_time = datetime.now()
        self.question_answers = []
    
    def submit_answer(self, user_id: int, answer_index: int) -> bool:
        """Submit an answer for the current question"""
        if user_id not in self.players or self.question_start_time is None:
            return False
        
        # Check if player already answered
        if any(ans.player_id == user_id for ans in self.question_answers):
            return False
        
        # Calculate answer time
        answer_time = (datetime.now() - self.question_start_time).total_seconds()
        if answer_time > self.question_time_limit:
            return False
        
        # Create answer record
        answer = PlayerAnswer(user_id, answer_index, answer_time)
        current_question = self.get_current_question()
        
        if current_question:
            answer.is_correct = answer_index == current_question.correct_index
            if answer.is_correct:
                # Calculate points: max 1000, decreasing with time
                # Points = 1000 * (remaining_time / total_time)
                remaining_time = max(0, self.question_time_limit - answer_time)
                answer.points_earned = int(1000 * (remaining_time / self.question_time_limit))
                self.players[user_id].score += answer.points_earned
        
        self.question_answers.append(answer)
        return True
    
    def get_leaderboard(self, include_changes: bool = False) -> List[Dict]:
        """Get current leaderboard with optional position changes and points added"""
        leaderboard = []
        
        # Get points added in current question for each player
        current_question_points = {}
        for answer in self.question_answers:
            current_question_points[answer.player_id] = answer.points_earned
        
        for player in self.players.values():
            player_data = {
                "user_id": player.user_id,
                "name": player.name,
                "score": player.score,
                "is_connected": player.is_connected
            }
            
            if include_changes:
                # Add points earned in current question
                points_added = current_question_points.get(player.user_id, 0)
                player_data["points_added"] = points_added
                
                # Calculate position change from previous question
                previous_rank = None
                if self.previous_leaderboard:
                    for prev_player in self.previous_leaderboard:
                        if prev_player["user_id"] == player.user_id:
                            previous_rank = prev_player["rank"]
                            break
                
                player_data["previous_rank"] = previous_rank
            
            leaderboard.append(player_data)
        
        # Sort by score descending
        leaderboard.sort(key=lambda x: x["score"], reverse=True)
        
        # Add current ranks and calculate position changes
        for i, player in enumerate(leaderboard):
            current_rank = i + 1
            player["rank"] = current_rank
            
            if include_changes and player.get("previous_rank") is not None:
                # Calculate position change (negative means moved up, positive means moved down)
                position_change = player["previous_rank"] - current_rank
                player["position_change"] = position_change
                
                # Add visual indicators
                if position_change > 0:
                    player["change_indicator"] = "up"  # Moved up
                    player["change_text"] = f"+{position_change}"
                elif position_change < 0:
                    player["change_indicator"] = "down"  # Moved down  
                    player["change_text"] = str(position_change)
                else:
                    player["change_indicator"] = "same"  # No change
                    player["change_text"] = "0"
            elif include_changes:
                # New player, no previous rank
                player["position_change"] = 0
                player["change_indicator"] = "new"
                player["change_text"] = "NEW"
        
        return leaderboard
    
    def update_previous_leaderboard(self):
        """Store current leaderboard as previous for next question comparison"""
        self.previous_leaderboard = self.get_leaderboard(include_changes=False)
    
    def next_question(self) -> bool:
        """Move to next question"""
        self.current_question_index += 1
        return self.current_question_index < len(self.questions)
    
    def is_finished(self) -> bool:
        """Check if quiz is finished"""
        return self.current_question_index >= len(self.questions)

# Global storage for active quiz rooms
active_rooms: Dict[str, QuizRoom] = {}

def generate_room_code() -> str:
    """Generate a unique 3-digit room code"""
    while True:
        code = ''.join(random.choices(string.digits, k=3))
        if code not in active_rooms:
            return code

def create_quiz_room(teacher_id: int, teacher_name: str, teacher_socket_id: str, 
                     lesson_ids: List[int], num_questions: int, is_locked: bool = False) -> str:
    """Create a new quiz room"""
    code = generate_room_code()
    room = QuizRoom(code, teacher_id, teacher_name, teacher_socket_id, 
                   lesson_ids, num_questions, is_locked)
    active_rooms[code] = room
    return code

def get_room(code: str) -> Optional[QuizRoom]:
    """Get a room by code"""
    return active_rooms.get(code)

def remove_room(code: str) -> bool:
    """Remove a room"""
    if code in active_rooms:
        del active_rooms[code]
        return True
    return False

def get_public_rooms() -> List[Dict]:
    """Get list of public (not locked) rooms that are waiting"""
    public_rooms = []
    for code, room in active_rooms.items():
        if not room.is_locked and room.status == QuizStatus.WAITING:
            public_rooms.append({
                "code": code,
                "teacher_name": room.teacher_name,
                "players_count": len(room.players),
                "num_questions": room.num_questions,
                "created_at": room.created_at.isoformat()
            })
    return public_rooms

def cleanup_disconnected_rooms():
    """Clean up rooms with no active connections (can be called periodically)"""
    rooms_to_remove = []
    for code, room in active_rooms.items():
        # Remove rooms older than 2 hours or with no connected players
        if (datetime.now() - room.created_at).total_seconds() > 7200:
            rooms_to_remove.append(code)
    
    for code in rooms_to_remove:
        remove_room(code)
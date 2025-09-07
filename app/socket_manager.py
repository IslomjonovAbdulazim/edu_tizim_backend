"""
Socket.IO manager for real-time quiz functionality
"""
import socketio
import asyncio
from typing import Dict, Optional
from datetime import datetime
from .quiz_models import (
    active_rooms, get_room, QuizStatus, cleanup_disconnected_rooms
)
from .database import SessionLocal
from .models import User, Word, Lesson
from .utils import verify_token
import random

# Create Socket.IO server
sio = socketio.AsyncServer(
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True
)

# Store socket connections: socket_id -> user_info
connected_users: Dict[str, Dict] = {}

# Store user sockets: user_id -> socket_id  
user_sockets: Dict[int, str] = {}

async def authenticate_socket(token: str) -> Optional[Dict]:
    """Authenticate user from JWT token"""
    try:
        payload = verify_token(token)
        if not payload:
            return None
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(
                User.id == payload["user_id"],
                User.is_active == True
            ).first()
            
            if user:
                return {
                    "user_id": user.id,
                    "role": user.role.value,
                    "name": getattr(user, 'phone', f"User {user.id}") or f"User {user.id}"
                }
        finally:
            db.close()
    except Exception as e:
        print(f"Socket auth error: {e}")
    
    return None

@sio.event
async def connect(sid, environ):
    """Handle client connection"""
    print(f"Client {sid} connected")
    
    # Get auth token from query params
    query_string = environ.get('QUERY_STRING', '')
    token = None
    
    for param in query_string.split('&'):
        if param.startswith('token='):
            token = param.split('=')[1]
            break
    
    if not token:
        print(f"No token provided for {sid}")
        await sio.disconnect(sid)
        return
    
    # Authenticate user
    user_info = await authenticate_socket(token)
    if not user_info:
        print(f"Authentication failed for {sid}")
        await sio.disconnect(sid)
        return
    
    # Store connection
    connected_users[sid] = user_info
    user_sockets[user_info["user_id"]] = sid
    
    print(f"User {user_info['name']} ({user_info['user_id']}) connected with socket {sid}")
    
    # Send connection success
    await sio.emit('connected', {
        'user_id': user_info["user_id"],
        'name': user_info["name"],
        'role': user_info["role"]
    }, room=sid)

@sio.event
async def disconnect(sid):
    """Handle client disconnection"""
    if sid in connected_users:
        user_info = connected_users[sid]
        user_id = user_info["user_id"]
        
        print(f"User {user_info['name']} ({user_id}) disconnected")
        
        # Remove from connected users
        del connected_users[sid]
        if user_id in user_sockets and user_sockets[user_id] == sid:
            del user_sockets[user_id]
        
        # Handle room disconnection
        for room_code, room in active_rooms.items():
            if user_id == room.teacher_id:
                # Teacher disconnected - notify all players
                await sio.emit('teacher_disconnected', {
                    'message': 'Teacher disconnected. Quiz ended.'
                }, room=f"room_{room_code}")
                
                # End the quiz
                room.status = QuizStatus.FINISHED
                
            elif user_id in room.players:
                # Student disconnected
                room.players[user_id].is_connected = False
                
                # Notify room about player leaving
                await sio.emit('player_left', {
                    'user_id': user_id,
                    'name': room.players[user_id].name,
                    'players_count': len([p for p in room.players.values() if p.is_connected])
                }, room=f"room_{room_code}")

@sio.event
async def join_room_socket(sid, data):
    """Handle student joining quiz room via socket"""
    if sid not in connected_users:
        await sio.emit('error', {'message': 'Not authenticated'}, room=sid)
        return
    
    user_info = connected_users[sid]
    room_code = data.get('room_code')
    
    if not room_code or user_info["role"] != "student":
        await sio.emit('error', {'message': 'Invalid request'}, room=sid)
        return
    
    room = get_room(room_code)
    if not room:
        await sio.emit('error', {'message': 'Room not found'}, room=sid)
        return
    
    if room.status != QuizStatus.WAITING:
        await sio.emit('error', {'message': 'Room is not accepting new players'}, room=sid)
        return
    
    # Add player to room
    if room.add_player(user_info["user_id"], user_info["name"], sid):
        # Join socket room
        await sio.enter_room(sid, f"room_{room_code}")
        
        # Notify player
        await sio.emit('room_joined', {
            'room_code': room_code,
            'teacher_name': room.teacher_name,
            'players_count': len(room.players)
        }, room=sid)
        
        # Notify all players in room
        await sio.emit('player_joined', {
            'user_id': user_info["user_id"],
            'name': user_info["name"],
            'players_count': len(room.players)
        }, room=f"room_{room_code}")
    else:
        await sio.emit('error', {'message': 'Could not join room'}, room=sid)

@sio.event
async def leave_room_socket(sid, data):
    """Handle student leaving quiz room"""
    if sid not in connected_users:
        return
    
    user_info = connected_users[sid]
    room_code = data.get('room_code')
    
    room = get_room(room_code)
    if room and user_info["user_id"] in room.players:
        # Remove from room
        room.remove_player(user_info["user_id"])
        await sio.leave_room(sid, f"room_{room_code}")
        
        # Notify room
        await sio.emit('player_left', {
            'user_id': user_info["user_id"],
            'name': user_info["name"],
            'players_count': len(room.players)
        }, room=f"room_{room_code}")

@sio.event
async def submit_answer_socket(sid, data):
    """Handle student submitting answer"""
    if sid not in connected_users:
        return
    
    user_info = connected_users[sid]
    room_code = data.get('room_code')
    answer_index = data.get('answer_index')
    
    if user_info["role"] != "student":
        return
    
    room = get_room(room_code)
    if not room or room.status != QuizStatus.IN_PROGRESS:
        await sio.emit('error', {'message': 'Cannot submit answer now'}, room=sid)
        return
    
    # Submit answer
    success = room.submit_answer(user_info["user_id"], answer_index)
    
    if success:
        # Notify player their answer was recorded
        await sio.emit('answer_submitted', {
            'answer_index': answer_index,
            'timestamp': datetime.now().isoformat()
        }, room=sid)
        
        # Notify teacher about answer count
        teacher_sid = user_sockets.get(room.teacher_id)
        if teacher_sid:
            await sio.emit('answer_received', {
                'player_name': user_info["name"],
                'answers_count': len(room.question_answers),
                'total_players': len(room.players)
            }, room=teacher_sid)

async def start_question_timer(room_code: str):
    """Start countdown timer for current question"""
    room = get_room(room_code)
    if not room:
        return
    
    # Emit question start to all players
    question = room.get_current_question()
    if not question:
        return
    
    question_data = {
        'word': question.word,
        'options': question.options,
        'question_number': room.current_question_index + 1,
        'total_questions': len(room.questions),
        'time_limit': room.question_time_limit
    }
    
    await sio.emit('question_started', question_data, room=f"room_{room_code}")
    
    # Start countdown
    for remaining in range(room.question_time_limit, 0, -1):
        await asyncio.sleep(1)
        
        # Check if question was manually ended
        current_room = get_room(room_code)
        if not current_room or current_room.status != QuizStatus.IN_PROGRESS:
            return
        
        await sio.emit('countdown', {'remaining': remaining}, room=f"room_{room_code}")
    
    # Time's up
    await end_current_question(room_code)

async def end_current_question(room_code: str):
    """End current question and show results"""
    room = get_room(room_code)
    if not room:
        return
    
    room.status = QuizStatus.QUESTION_ENDED
    question = room.get_current_question()
    
    if question:
        # Get enhanced leaderboard with position changes and points added
        enhanced_leaderboard = room.get_leaderboard(include_changes=True)
        
        # Prepare results
        results = {
            'question': {
                'word': question.word,
                'options': question.options,
                'correct_answer': question.correct_answer,
                'correct_index': question.correct_index
            },
            'leaderboard': enhanced_leaderboard,
            'answers_count': len(room.question_answers),
            'total_players': len(room.players),
            'question_number': room.current_question_index + 1,
            'total_questions': len(room.questions)
        }
        
        # Send results to all players
        await sio.emit('question_ended', results, room=f"room_{room_code}")
        
        # Update previous leaderboard for next question comparison
        room.update_previous_leaderboard()

async def notify_public_rooms_update():
    """Notify all connected users about public rooms update"""
    from .quiz_models import get_public_rooms
    public_rooms = get_public_rooms()
    
    # Send to all students
    for sid, user_info in connected_users.items():
        if user_info["role"] == "student":
            await sio.emit('public_rooms_updated', {'rooms': public_rooms}, room=sid)

# Periodic cleanup will be handled by the scheduler in main.py
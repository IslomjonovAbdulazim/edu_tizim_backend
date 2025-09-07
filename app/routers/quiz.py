"""
Quiz system endpoints for teachers and students
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import random

from ..database import get_db
from ..models import User, Word, Lesson, Module, Course
from ..dependencies import get_current_user
from ..utils import APIResponse
from ..quiz_models import (
    create_quiz_room, get_room, active_rooms, get_public_rooms,
    QuizStatus, QuizQuestion, remove_room
)
from ..quiz_schemas import (
    CreateQuizRoomRequest, StartQuizRequest, NextQuestionRequest, SkipQuestionRequest,
    JoinRoomRequest, QuizRoomResponse, QuizErrorResponse
)
from ..socket_manager import (
    sio, start_question_timer, end_current_question, notify_public_rooms_update,
    user_sockets
)

router = APIRouter()

def get_teacher_user(current_user: dict = Depends(get_current_user)):
    """Ensure user is a teacher"""
    if current_user["role"] != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this endpoint"
        )
    return current_user

def get_student_user(current_user: dict = Depends(get_current_user)):
    """Ensure user is a student"""
    if current_user["role"] != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access this endpoint"
        )
    return current_user

async def generate_quiz_questions(db: Session, lesson_ids: List[int], num_questions: int) -> List[QuizQuestion]:
    """Generate quiz questions from selected lessons"""
    # Get all words from selected lessons
    words = db.query(Word).join(Lesson).filter(
        Lesson.id.in_(lesson_ids),
        Lesson.is_active == True,
        Word.is_active == True
    ).all()
    
    if len(words) < num_questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough words in selected lessons. Found {len(words)}, need {num_questions}"
        )
    
    # Randomly select questions
    selected_words = random.sample(words, num_questions)
    questions = []
    
    for word in selected_words:
        # Get other words for wrong options (from same lessons)
        other_words = [w for w in words if w.id != word.id]
        wrong_options = random.sample(other_words, min(3, len(other_words)))
        
        # Create 4 options (1 correct + 3 wrong)
        options = [word.meaning]  # Correct answer
        for wrong_word in wrong_options:
            options.append(wrong_word.meaning)
        
        # If we don't have enough wrong options, create some generic ones
        while len(options) < 4:
            options.append(f"Option {len(options)}")
        
        # Shuffle options
        random.shuffle(options)
        
        question = QuizQuestion(
            word_id=word.id,
            word=word.word,
            meaning=word.meaning,
            options=options,
            correct_answer=word.meaning
        )
        questions.append(question)
    
    return questions

# Teacher Endpoints

@router.post("/teacher/create-room")
async def create_room(
    request: CreateQuizRoomRequest,
    teacher: dict = Depends(get_teacher_user),
    db: Session = Depends(get_db)
):
    """Create a new quiz room"""
    try:
        print(f"🎯 Creating quiz room for teacher {teacher['user'].id}")
        print(f"🎯 Request: lessons={request.lesson_ids}, questions={request.num_questions}, locked={request.is_locked}")
        
        # Verify lessons exist and teacher has access
        lessons = db.query(Lesson).join(Module).join(Course).filter(
            Lesson.id.in_(request.lesson_ids),
            Lesson.is_active == True,
            Module.is_active == True,
            Course.is_active == True
        ).all()
        
        print(f"🎯 Found {len(lessons)} lessons out of {len(request.lesson_ids)} requested")
        
        if len(lessons) != len(request.lesson_ids):
            missing_ids = set(request.lesson_ids) - set(l.id for l in lessons)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lessons not found or not accessible: {missing_ids}"
            )
        
        # Generate questions
        questions = await generate_quiz_questions(db, request.lesson_ids, request.num_questions)
        
        # Get teacher socket ID
        print(f"🎯 Checking teacher socket connection...")
        print(f"🎯 user_sockets keys: {list(user_sockets.keys())}")
        teacher_socket_id = user_sockets.get(teacher["user"].id, "")
        print(f"🎯 Teacher socket ID: '{teacher_socket_id}'")
        
        # Temporarily disable Socket.IO requirement for debugging
        if not teacher_socket_id:
            print(f"⚠️ Teacher not connected via WebSocket, using fallback")
            teacher_socket_id = "fallback_socket_id"
            # raise HTTPException(
            #     status_code=status.HTTP_400_BAD_REQUEST,
            #     detail="Teacher must be connected via WebSocket to create quiz"
            # )
        
        # Get teacher name safely
        teacher_name = f"Teacher {teacher['user'].id}"
        if teacher.get("profile") and hasattr(teacher["profile"], "full_name"):
            teacher_name = teacher["profile"].full_name or teacher_name
        
        print(f"🎯 Teacher name: {teacher_name}")
        
        # Create room
        room_code = create_quiz_room(
            teacher_id=teacher["user"].id,
            teacher_name=teacher_name,
            teacher_socket_id=teacher_socket_id,
            lesson_ids=request.lesson_ids,
            num_questions=request.num_questions,
            is_locked=request.is_locked
        )
        
        room = get_room(room_code)
        if room:
            room.questions = questions
            
            # Join teacher to socket room only if they have a real socket connection
            if teacher_socket_id != "fallback_socket_id":
                try:
                    await sio.enter_room(teacher_socket_id, f"room_{room_code}")
                    print(f"✅ Teacher joined socket room_{room_code}")
                except Exception as e:
                    print(f"⚠️ Failed to join socket room: {e}")
            else:
                print(f"⚠️ Skipping socket room join (fallback mode)")
            
            # Notify about new public room
            if not request.is_locked:
                try:
                    await notify_public_rooms_update()
                    print(f"✅ Public rooms updated")
                except Exception as e:
                    print(f"⚠️ Failed to update public rooms: {e}")
            
            return APIResponse.success({
                "room_code": room_code,
                "questions_count": len(questions),
                "is_locked": request.is_locked,
                "message": "Quiz room created successfully"
            })
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create quiz room: {str(e)}"
        )

@router.post("/teacher/start-quiz")
async def start_quiz(
    request: StartQuizRequest,
    teacher: dict = Depends(get_teacher_user)
):
    """Start the quiz"""
    room = get_room(request.room_code)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room.teacher_id != teacher["user"].id:
        raise HTTPException(status_code=403, detail="Only room creator can start quiz")
    
    if room.status != QuizStatus.WAITING:
        raise HTTPException(status_code=400, detail="Quiz cannot be started in current state")
    
    if len(room.players) == 0:
        raise HTTPException(status_code=400, detail="No players in room")
    
    # Start quiz
    room.status = QuizStatus.IN_PROGRESS
    room.current_question_index = 0
    room.start_question()
    
    # Notify all participants
    await sio.emit('quiz_started', {
        'message': 'Quiz is starting!',
        'total_questions': len(room.questions)
    }, room=f"room_{request.room_code}")
    
    # Start first question timer
    await start_question_timer(request.room_code)
    
    return APIResponse.success({"message": "Quiz started successfully"})

@router.post("/teacher/next-question")
async def next_question(
    request: NextQuestionRequest,
    teacher: dict = Depends(get_teacher_user)
):
    """Move to next question"""
    room = get_room(request.room_code)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room.teacher_id != teacher["user"].id:
        raise HTTPException(status_code=403, detail="Only room creator can control quiz")
    
    if room.status != QuizStatus.QUESTION_ENDED:
        raise HTTPException(status_code=400, detail="Cannot advance question now")
    
    # Move to next question
    if room.next_question():
        # Start next question
        room.status = QuizStatus.IN_PROGRESS
        room.start_question()
        await start_question_timer(request.room_code)
        
        return APIResponse.success({"message": "Next question started"})
    else:
        # Quiz finished
        room.status = QuizStatus.FINISHED
        
        # Send final results
        await sio.emit('quiz_finished', {
            'final_leaderboard': room.get_leaderboard(),
            'total_questions': len(room.questions)
        }, room=f"room_{request.room_code}")
        
        # Remove room after 30 seconds
        import asyncio
        asyncio.create_task(delayed_room_removal(request.room_code, 30))
        
        return APIResponse.success({"message": "Quiz finished"})

@router.post("/teacher/skip-question")
async def skip_question(
    request: SkipQuestionRequest,
    teacher: dict = Depends(get_teacher_user)
):
    """Skip current question"""
    room = get_room(request.room_code)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room.teacher_id != teacher["user"].id:
        raise HTTPException(status_code=403, detail="Only room creator can control quiz")
    
    if room.status != QuizStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="No active question to skip")
    
    # End current question immediately
    await end_current_question(request.room_code)
    
    return APIResponse.success({"message": "Question skipped"})

@router.get("/teacher/room-status/{room_code}")
async def get_room_status(
    room_code: str,
    teacher: dict = Depends(get_teacher_user)
):
    """Get current room status"""
    room = get_room(room_code)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room.teacher_id != teacher["user"].id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return APIResponse.success({
        "code": room.code,
        "status": room.status.value,
        "players": [
            {
                "user_id": p.user_id,
                "name": p.name,
                "score": p.score,
                "is_connected": p.is_connected
            } for p in room.players.values()
        ],
        "current_question": room.current_question_index + 1 if room.current_question_index < len(room.questions) else None,
        "total_questions": len(room.questions),
        "answers_received": len(room.question_answers) if room.status == QuizStatus.IN_PROGRESS else 0
    })

# Student Endpoints

@router.get("/student/public-rooms")
async def get_public_rooms_endpoint(student: dict = Depends(get_student_user)):
    """Get list of public quiz rooms"""
    public_rooms = get_public_rooms()
    return APIResponse.success({"rooms": public_rooms})

@router.post("/student/join-room")
async def join_room_endpoint(
    request: JoinRoomRequest,
    student: dict = Depends(get_student_user)
):
    """Join a quiz room (also handled via WebSocket)"""
    room = get_room(request.room_code)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room.status != QuizStatus.WAITING:
        raise HTTPException(status_code=400, detail="Room is not accepting new players")
    
    student_socket_id = user_sockets.get(student["user"].id, "")
    if not student_socket_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student must be connected via WebSocket to join quiz"
        )
    
    student_name = student.get("profile", {}).get("full_name", f"Student {student['user'].id}") or f"Student {student['user'].id}"
    
    if room.add_player(student["user"].id, student_name, student_socket_id):
        # Join socket room
        await sio.enter_room(student_socket_id, f"room_{request.room_code}")
        
        # Notify all players
        await sio.emit('player_joined', {
            'user_id': student["user"].id,
            'name': student_name,
            'players_count': len(room.players)
        }, room=f"room_{request.room_code}")
        
        return APIResponse.success({
            "room_code": request.room_code,
            "teacher_name": room.teacher_name,
            "players_count": len(room.players)
        })
    else:
        raise HTTPException(status_code=400, detail="Could not join room")

# Utility functions
async def delayed_room_removal(room_code: str, delay_seconds: int):
    """Remove room after delay"""
    import asyncio
    await asyncio.sleep(delay_seconds)
    remove_room(room_code)
    await notify_public_rooms_update()
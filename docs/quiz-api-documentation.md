# Quiz System API Documentation

## Overview
Real-time Kahoot-style quiz system with WebSocket connections for live gameplay.

## Authentication
All endpoints require JWT authentication via `Authorization: Bearer <token>` header.

## Base URL
- **HTTP API**: `http://localhost:8000/api/quiz/`
- **WebSocket**: `ws://localhost:8000/socket.io/?token=<jwt_token>`

---

## 👨‍🏫 Teacher Endpoints

### 1. Create Quiz Room
**Creates a new quiz room with questions from selected lessons.**

```http
POST /api/quiz/teacher/create-room
```

**Headers:**
```
Authorization: Bearer <teacher_jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "lesson_ids": [1, 2, 3],
  "num_questions": 10,
  "is_locked": false
}
```

**Request Parameters:**
- `lesson_ids` (array of integers, required): List of lesson IDs to pull words from
- `num_questions` (integer, required): Number of questions (1-100)
- `is_locked` (boolean, optional): If true, room is private (join by code only). Default: false

**Response:**
```json
{
  "success": true,
  "data": {
    "room_code": "123",
    "questions_count": 10,
    "is_locked": false,
    "message": "Quiz room created successfully"
  }
}
```

**Behavior:**
- Teacher must be connected via WebSocket to create room
- Generates unique 3-digit room code
- Creates questions by randomly selecting words from specified lessons
- Public rooms appear in student's room list
- Room automatically expires after 2 hours

---

### 2. Start Quiz
**Begins the quiz for all players in the room.**

```http
POST /api/quiz/teacher/start-quiz
```

**Request Body:**
```json
{
  "room_code": "123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Quiz started successfully"
  }
}
```

**Behavior:**
- Only room creator can start quiz
- Requires at least 1 player in room
- Changes room status from `waiting` to `in_progress`
- Sends `quiz_started` WebSocket event to all players
- Automatically begins first question with 20-second timer

---

### 3. Next Question
**Advances to the next question after current question ends.**

```http
POST /api/quiz/teacher/next-question
```

**Request Body:**
```json
{
  "room_code": "123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Next question started"
  }
}
```

**OR if quiz finished:**
```json
{
  "success": true,
  "data": {
    "message": "Quiz finished"
  }
}
```

**Behavior:**
- Only available when current question has ended
- If more questions remain: starts next question with timer
- If no more questions: ends quiz and shows final results
- Room automatically deleted after 30 seconds when finished

---

### 4. Skip Question
**Immediately ends current question and shows results.**

```http
POST /api/quiz/teacher/skip-question
```

**Request Body:**
```json
{
  "room_code": "123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Question skipped"
  }
}
```

**Behavior:**
- Only available during active question (timer running)
- Stops countdown timer
- Shows correct answer and leaderboard
- Teacher can then advance to next question

---

### 5. Room Status
**Gets current room information and statistics.**

```http
GET /api/quiz/teacher/room-status/{room_code}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "code": "123",
    "status": "in_progress",
    "players": [
      {
        "user_id": 1,
        "name": "Student Name",
        "score": 2750,
        "is_connected": true
      }
    ],
    "current_question": 3,
    "total_questions": 10,
    "answers_received": 2
  }
}
```

**Status Values:**
- `waiting`: Room created, accepting players
- `in_progress`: Quiz running, question active
- `question_ended`: Question finished, showing results
- `finished`: Quiz completed

**Behavior:**
- Real-time snapshot of room state
- Shows all players with current scores
- Tracks answer submission progress
- Only accessible by room creator

---

## 🧑‍🎓 Student Endpoints

### 1. Get Public Rooms
**Lists all available public quiz rooms.**

```http
GET /api/quiz/student/public-rooms
```

**Headers:**
```
Authorization: Bearer <student_jwt_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "rooms": [
      {
        "code": "123",
        "teacher_name": "Teacher Name",
        "players_count": 5,
        "num_questions": 10,
        "created_at": "2023-12-07T10:30:00Z"
      }
    ]
  }
}
```

**Behavior:**
- Only shows public rooms (not locked)
- Only shows rooms in `waiting` status
- Updated in real-time via WebSocket events
- Empty array if no public rooms available

---

### 2. Join Room (HTTP)
**Joins a quiz room via HTTP request.**

```http
POST /api/quiz/student/join-room
```

**Request Body:**
```json
{
  "room_code": "123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "room_code": "123",
    "teacher_name": "Teacher Name",
    "players_count": 6
  }
}
```

**Behavior:**
- Student must be connected via WebSocket
- Only works for rooms in `waiting` status
- Also joins WebSocket room for real-time events
- Notifies all players of new participant
- Alternative to WebSocket `join_room_socket` event

---

## 🌐 WebSocket Events

### Connection
Connect to WebSocket with JWT token in query parameter:
```
ws://localhost:8000/socket.io/?token=<jwt_token>
```

---

## 📡 WebSocket Events (Client → Server)

### Join Room (Student Only)
```javascript
socket.emit('join_room_socket', {
  room_code: '123'
});
```

### Leave Room (Student Only)
```javascript
socket.emit('leave_room_socket', {
  room_code: '123'
});
```

### Submit Answer (Student Only)
```javascript
socket.emit('submit_answer_socket', {
  room_code: '123',
  answer_index: 2  // 0-3 for options A-D
});
```

---

## 📨 WebSocket Events (Server → Client)

### Connection Events

#### Connected
```javascript
socket.on('connected', (data) => {
  // data: { user_id, name, role }
});
```

#### Error
```javascript
socket.on('error', (data) => {
  // data: { message }
});
```

### Room Events (Both Roles)

#### Room Joined (Student)
```javascript
socket.on('room_joined', (data) => {
  // data: { room_code, teacher_name, players_count }
});
```

#### Player Joined
```javascript
socket.on('player_joined', (data) => {
  // data: { user_id, name, players_count }
});
```

#### Player Left
```javascript
socket.on('player_left', (data) => {
  // data: { user_id, name, players_count }
});
```

#### Teacher Disconnected
```javascript
socket.on('teacher_disconnected', (data) => {
  // data: { message: "Teacher disconnected. Quiz ended." }
});
```

### Quiz Flow Events (Both Roles)

#### Quiz Started
```javascript
socket.on('quiz_started', (data) => {
  // data: { message, total_questions }
});
```

#### Question Started
```javascript
socket.on('question_started', (data) => {
  // data: {
  //   word: "hello",
  //   options: ["salom", "xayr", "rahmat", "iltimos"],
  //   question_number: 1,
  //   total_questions: 10,
  //   time_limit: 20
  // }
});
```

#### Countdown Timer
```javascript
socket.on('countdown', (data) => {
  // data: { remaining: 15 }  // seconds left
});
```

#### Question Ended
```javascript
socket.on('question_ended', (data) => {
  // data: {
  //   question: { word, options, correct_answer, correct_index },
  //   leaderboard: [{
  //     rank: 1,
  //     user_id: 123,
  //     name: "Student Name",
  //     score: 2750,
  //     is_connected: true,
  //     points_added: 750,        // Points earned this question
  //     previous_rank: 2,         // Rank before this question
  //     position_change: 1,       // Moved up 1 position
  //     change_indicator: "up",   // "up", "down", "same", "new"
  //     change_text: "+1"         // Display text for position change
  //   }],
  //   answers_count: 5,
  //   total_players: 8,
  //   question_number: 1,
  //   total_questions: 10
  // }
});
```

#### Quiz Finished
```javascript
socket.on('quiz_finished', (data) => {
  // data: {
  //   final_leaderboard: [{ rank, user_id, name, score }],
  //   total_questions: 10
  // }
});
```

### Answer Events

#### Answer Submitted (Student)
```javascript
socket.on('answer_submitted', (data) => {
  // data: { answer_index, timestamp }
});
```

#### Answer Received (Teacher)
```javascript
socket.on('answer_received', (data) => {
  // data: { player_name, answers_count, total_players }
});
```

### Student-Specific Events

#### Public Rooms Updated
```javascript
socket.on('public_rooms_updated', (data) => {
  // data: { rooms: [{ code, teacher_name, players_count, num_questions, created_at }] }
});
```

---

## 🎯 Scoring System

### Points Calculation
- **Maximum**: 1000 points per question
- **Formula**: `points = 1000 × (remaining_time / 20)`
- **Examples**:
  - Answer in 1 second: 950 points
  - Answer in 10 seconds: 500 points
  - Answer in 19 seconds: 50 points
  - Wrong answer or timeout: 0 points

### Enhanced Leaderboard
After each question, the leaderboard shows:

#### Position Changes
- **⬆️ Up**: Player moved to higher rank (green, e.g., "+2")
- **⬇️ Down**: Player dropped in rank (red, e.g., "-1") 
- **➡️ Same**: Player maintained same rank (gray, "0")
- **🆕 New**: Player joining mid-quiz (blue, "NEW")

#### Points Display
- **Current Score**: Total accumulated points
- **Points Added**: Points earned in the current question (e.g., "+750 pts")
- **Previous Rank**: Where player was ranked before this question

#### Leaderboard Data Structure
```json
{
  "rank": 1,
  "user_id": 123,
  "name": "Student Name", 
  "score": 2750,
  "is_connected": true,
  "points_added": 750,
  "previous_rank": 2,
  "position_change": 1,
  "change_indicator": "up",
  "change_text": "+1"
}
```

#### Visual Examples
- **1st Place**: `🥇 1. Alice - 2750 points (+750 pts) ⬆️ +1`
- **2nd Place**: `🥈 2. Bob - 2500 points (+500 pts) ⬇️ -1`  
- **3rd Place**: `🥉 3. Charlie - 2000 points (+0 pts) ➡️ 0`
- **New Player**: `🏆 4. David - 800 points (+800 pts) 🆕 NEW`

---

## 🔄 Game Flow

1. **Room Creation**: Teacher creates room → gets 3-digit code
2. **Player Joining**: Students join via code or public room list
3. **Quiz Start**: Teacher starts quiz → all players notified
4. **Question Loop**:
   - Question appears for all players simultaneously
   - 20-second countdown begins
   - Students submit answers via WebSocket
   - Timer expires or teacher skips → results shown
   - Teacher advances to next question
5. **Quiz End**: Final leaderboard → room cleanup after 30 seconds

---

## ❌ Error Responses

### Common HTTP Errors
```json
{
  "success": false,
  "message": "Room not found",
  "detail": "The specified room code does not exist"
}
```

**Error Codes:**
- `400`: Bad request (invalid parameters, room in wrong state)
- `401`: Unauthorized (invalid/missing JWT token)
- `403`: Forbidden (wrong role, not room creator)
- `404`: Not found (room doesn't exist)
- `500`: Internal server error

### WebSocket Errors
```javascript
socket.on('error', (data) => {
  // Common error messages:
  // "Not authenticated"
  // "Room not found"
  // "Room is not accepting new players"
  // "Cannot submit answer now"
  // "Could not join room"
});
```

---

## 📋 Usage Examples

### Teacher Flow
```javascript
// 1. Create room
fetch('/api/quiz/teacher/create-room', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + teacherToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    lesson_ids: [1, 2, 3],
    num_questions: 5,
    is_locked: false
  })
});

// 2. Start quiz when ready
fetch('/api/quiz/teacher/start-quiz', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + teacherToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    room_code: '123'
  })
});

// 3. Control questions via WebSocket events
socket.on('question_ended', () => {
  // Teacher can now advance to next question
});
```

### Student Flow
```javascript
// 1. Connect and join room
const socket = io('ws://localhost:8000/socket.io/', {
  query: { token: studentToken }
});

// 2. Join room
socket.emit('join_room_socket', {
  room_code: '123'
});

// 3. Answer questions
socket.on('question_started', (question) => {
  // Show question UI
  // User selects option 2
  socket.emit('submit_answer_socket', {
    room_code: '123',
    answer_index: 2
  });
});

// 4. View results
socket.on('question_ended', (results) => {
  // Show correct answer and leaderboard
});
```

---

## 🔧 Technical Notes

- **In-Memory Storage**: No database persistence - all data lost on server restart
- **Room Cleanup**: Automatic removal of inactive rooms every 5 minutes
- **Connection Limits**: No built-in limits (configure at infrastructure level)
- **Scalability**: Single server instance (use Redis adapter for multi-server)
- **WebSocket Library**: Socket.IO with fallback support
- **Authentication**: JWT tokens required for all operations
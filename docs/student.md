# Student Endpoints Documentation

This document covers all API endpoints available for student users in the education platform.

## Base URL
All endpoints are prefixed with the API base URL (e.g., `/api/v1`)

## Authentication

### Request Verification Code
**POST** `/student/request-code`

Request an SMS/Telegram verification code for student login.

**Request Body:**
```json
{
  "phone": "string"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "message": "Verification code sent to your Telegram",
    "phone": "+998901234567",
    "expires_in": 300
  }
}
```

**Error Cases:**
- `400`: Invalid phone number format
- `404`: Student not found with this phone number  
- `500`: Failed to send verification code

---

### Verify Code and Login
**POST** `/student/verify`

Verify the received code and complete student login.

**Request Body:**
```json
{
  "phone": "string",
  "code": "string"
}
```

**Response:**
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 2592000,
  "center_id": 123,
  "role": "student"
}
```

**Error Cases:**
- `400`: Phone and code are required
- `401`: Invalid or expired verification code
- `404`: User not found

---

### Telegram Direct Login
**POST** `/student/telegram-login`

Direct login using phone and Telegram ID (for bot integration).

**Request Body:**
```json
{
  "phone": "string",
  "telegram_id": "string"
}
```

**Response:**
```json
{
  "access_token": "string",
  "token_type": "bearer", 
  "expires_in": 2592000,
  "center_id": 123,
  "role": "student"
}
```

**Error Cases:**
- `400`: Invalid phone number or missing Telegram ID
- `401`: Invalid phone number or Telegram ID

## Content Access

All content endpoints require authentication. Include the access token in the `Authorization` header:
```
Authorization: Bearer <access_token>
```

### Get Courses
**GET** `/courses?center_id={center_id}`

Get all available courses for a learning center.

**Query Parameters:**
- `center_id` (required): Learning center ID

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "title": "English Basics",
      "description": "Foundation English course",
      "created_at": "2024-01-01T00:00:00"
    }
  ]
}
```

---

### Get Course Structure
**GET** `/courses/{course_id}`

Get complete course structure with modules and lessons.

**Path Parameters:**
- `course_id`: Course ID

**Response:**
```json
{
  "status": "success", 
  "data": {
    "id": 1,
    "title": "English Basics",
    "description": "Foundation course",
    "modules": [
      {
        "id": 1,
        "title": "Module 1",
        "lessons": [
          {
            "id": 1,
            "title": "Lesson 1",
            "words_count": 25
          }
        ]
      }
    ]
  }
}
```

---

### Get Lesson Words
**GET** `/lessons/{lesson_id}/words`

Get all words in a specific lesson.

**Path Parameters:**
- `lesson_id`: Lesson ID

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "word": "hello",
      "meaning": "salom",
      "definition": "A greeting",
      "example_sentence": "Hello, how are you?",
      "image_url": "https://example.com/hello.jpg",
      "audio_url": "https://example.com/hello.mp3",
      "lesson_id": 1
    }
  ]
}
```

---

### Get Word Details
**GET** `/words/{word_id}`

Get detailed information about a specific word.

**Path Parameters:**
- `word_id`: Word ID

**Response:**
```json
{
  "status": "success",
  "data": {
    "id": 1,
    "word": "hello",
    "meaning": "salom", 
    "definition": "A greeting used when meeting someone",
    "example_sentence": "Hello, how are you today?",
    "image_url": "https://example.com/hello.jpg",
    "audio_url": "https://example.com/hello.mp3"
  }
}
```

---

### Search Content
**GET** `/search`

Search through courses, lessons, and words.

**Query Parameters:**
- `q` (required): Search query (minimum 2 characters)
- `center_id` (required): Learning center ID
- `content_type`: Type to search (`courses`, `lessons`, `words`, `all`) - default: `all`
- `limit`: Maximum results (max 50) - default: 20

**Response:**
```json
{
  "status": "success",
  "data": {
    "courses": [
      {"id": 1, "title": "English Basics", "description": "Foundation course"}
    ],
    "lessons": [
      {"id": 1, "title": "Greetings", "module_id": 1}
    ],
    "words": [
      {"id": 1, "word": "hello", "meaning": "salom", "lesson_id": 1}
    ]
  }
}
```

---

### Get Random Words
**GET** `/random-words`

Get random words for practice sessions.

**Query Parameters:**
- `center_id` (required): Learning center ID
- `count`: Number of words (max 50) - default: 10

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "word": "hello",
      "meaning": "salom",
      "definition": "A greeting",
      "example_sentence": "Hello, how are you?",
      "image_url": "https://example.com/hello.jpg", 
      "audio_url": "https://example.com/hello.mp3",
      "lesson_id": 1
    }
  ]
}
```

## Progress Tracking

### Update Lesson Progress
**POST** `/progress/lesson`

Update progress for a specific lesson.

**Request Body:**
```json
{
  "lesson_id": 1,
  "percentage": 85
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "message": "Progress updated successfully"
  }
}
```

**Notes:**
- Percentage must be between 0-100
- Only students can update their own progress

---

### Update Word Progress
**POST** `/progress/word`

Record word practice attempts and update word-level progress.

**Request Body:**
```json
{
  "word_id": 1,
  "correct": true
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "message": "Word progress updated"
  }
}
```

**Notes:**
- Used for tracking correct/incorrect word attempts
- Helps identify weak words for review

---

### Get My Progress
**GET** `/my-progress`

Get comprehensive learning progress for the current student.

**Response:**
```json
{
  "status": "success",
  "data": {
    "progress": [
      {
        "lesson_id": 1,
        "percentage": 85,
        "completed": false,
        "last_practiced": "2024-01-01T12:00:00"
      }
    ],
    "summary": {
      "total_lessons": 25,
      "completed_lessons": 12,
      "total_coins": 150,
      "weak_words_count": 5
    },
    "weak_words": [
      {
        "id": 15,
        "word": "difficult",
        "meaning": "qiyin"
      }
    ]
  }
}
```

## Statistics

### Get Course Statistics
**GET** `/stats/{course_id}`

Get statistics for a specific course.

**Path Parameters:**
- `course_id`: Course ID

**Response:**
```json
{
  "status": "success",
  "data": {
    "course": {
      "id": 1,
      "title": "English Basics",
      "description": "Foundation English course"
    },
    "stats": {
      "modules": 5,
      "lessons": 25,
      "words": 500,
      "enrolled_students": 45
    }
  }
}
```

## Common Response Format

All endpoints follow a consistent response format:

**Success Response:**
```json
{
  "status": "success",
  "data": { ... },
  "message": "optional message"
}
```

**Error Response:**
```json
{
  "detail": "Error message"
}
```

## Authentication Requirements

- **No Auth Required:** `/student/request-code`, `/student/verify`, `/student/telegram-login`
- **Student Auth Required:** All other endpoints require valid student authentication
- **Token Expiry:** Access tokens expire after 30 days (2,592,000 seconds)

## Error Handling

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request (validation errors)
- `401`: Unauthorized (invalid/expired token)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found (resource doesn't exist)
- `500`: Internal Server Error

## Rate Limiting

- Verification code requests are limited by Redis TTL (5 minutes)
- Only one verification code can be active per phone number at a time

## Security Notes

- Students can only access content from their assigned learning center
- Phone numbers are automatically formatted and validated
- Verification codes expire after 5 minutes
- Students cannot access admin or teacher-specific functionality
- All student actions are scoped to their assigned learning center profile
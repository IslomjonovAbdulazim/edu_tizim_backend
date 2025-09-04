# Content API Endpoints

**Base URL:** `https://edutizimbackend-production.up.railway.app`

## Course Content

### GET /content/courses
Get available courses for a center

**Request Parameters:**
- `center_id` (int, required): Learning center ID

**Response (Success):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "title": "English Fundamentals",
      "description": "Basic English language course",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

**Response (No Courses):**
```json
{
  "success": true,
  "data": [],
  "message": "No courses found for this center"
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Access denied"
}
```

### GET /content/courses/{course_id}
Get complete course structure with modules and lessons

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "title": "English Fundamentals",
    "description": "Basic English language course",
    "modules": [
      {
        "id": 10,
        "title": "Grammar Basics",
        "description": "Introduction to English grammar",
        "order_index": 1,
        "lessons": [
          {
            "id": 20,
            "title": "Present Tense",
            "description": "Learning present tense verbs",
            "order_index": 1,
            "word_count": 15
          }
        ]
      }
    ]
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Course not found"
}
```

```json
{
  "success": false,
  "detail": "Course content not found"
}
```

### GET /content/lessons/{lesson_id}/words
Get all words in a lesson

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": [
    {
      "id": 30,
      "word": "apple",
      "meaning": "olma",
      "definition": "A round fruit with red or green skin",
      "example_sentence": "I eat an apple every day",
      "image_url": "/storage/word-images/abc123.jpg",
      "audio_url": "/storage/word-audio/def456.mp3",
      "order_index": 1
    }
  ]
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Lesson not found"
}
```

```json
{
  "success": false,
  "detail": "Access denied"
}
```

## Error Responses

All endpoints can return these common errors:

### Authentication Required
```json
{
  "success": false,
  "detail": "Not authenticated"
}
```

### Access Denied
```json
{
  "success": false,
  "detail": "Access denied"
}
```

### Server Error
```json
{
  "success": false,
  "detail": "Internal server error"
}
```
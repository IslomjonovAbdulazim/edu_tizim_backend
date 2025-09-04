# Admin API Endpoints

**Base URL:** `https://edutizimbackend-production.up.railway.app`

## Dashboard

### GET /admin/dashboard
Get admin dashboard with key metrics

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "stats": {
      "total_students": 75,
      "total_teachers": 5,
      "total_groups": 8,
      "total_courses": 3
    },
    "recent_students": [
      {
        "id": 123,
        "full_name": "John Doe",
        "created_at": "2024-01-15T10:30:00Z"
      }
    ],
    "center": {
      "title": "English Learning Hub",
      "days_remaining": 25,
      "student_limit": 100
    }
  }
}
```

## User Management

### POST /admin/users/students
Create new student account

**Request:**
```json
{
  "full_name": "John Doe",
  "phone": "+998901234567",
  "telegram_id": "@johndoe"
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "profile_id": 123,
    "message": "Student created successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Invalid Uzbekistan phone number format"
}
```

```json
{
  "success": false,
  "detail": "Student already exists in this center"
}
```

### POST /admin/users/teachers
Create new teacher account

**Request:**
```json
{
  "full_name": "Jane Smith",
  "email": "jane@example.com",
  "password": "securepassword123"
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "profile_id": 456,
    "message": "Teacher created successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Teacher already exists in this center"
}
```

### GET /admin/users/students
Get all students in center with pagination and search

**Request Parameters:**
- `page` (int, optional): Page number (default: 1)
- `size` (int, optional): Items per page (default: 20)
- `search` (string, optional): Search by student name

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 123,
        "user_id": 789,
        "center_id": 1,
        "full_name": "John Doe",
        "phone": "+998901234567",
        "role_in_center": "STUDENT",
        "is_active": true,
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
      }
    ],
    "total": 75,
    "page": 1,
    "size": 20
  }
}
```

### GET /admin/users/teachers
Get all teachers in center

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": [
    {
      "id": 456,
      "full_name": "Jane Smith",
      "email": "jane@example.com",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### PUT /admin/users/students/{profile_id}
Update student information

**Request:**
```json
{
  "full_name": "John Updated Doe"
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Student updated successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Student not found"
}
```

### PUT /admin/users/teachers/{profile_id}
Update teacher information

**Request:**
```json
{
  "full_name": "Jane Updated Smith",
  "password": "newpassword123"
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Teacher updated successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Teacher not found"
}
```

### DELETE /admin/users/students/{profile_id}
Soft delete student

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Student deleted successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Student not found"
}
```

### DELETE /admin/users/teachers/{profile_id}
Soft delete teacher

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Teacher deleted successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Teacher not found"
}
```

## Group Management

### POST /admin/groups
Create new group

**Request:**
```json
{
  "name": "Beginner English A1",
  "teacher_id": 456,
  "course_id": 1
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "group_id": 789,
    "message": "Group created successfully"
  }
}
```

### GET /admin/groups
Get all groups in center

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": [
    {
      "id": 789,
      "name": "Beginner English A1",
      "teacher_id": 456,
      "course_id": 1,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### PUT /admin/groups/{group_id}
Update group information

**Request:**
```json
{
  "name": "Updated Group Name",
  "teacher_id": 456,
  "course_id": 2
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Group updated successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Group not found"
}
```

### DELETE /admin/groups/{group_id}
Soft delete group

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Group deleted successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Group not found"
}
```

### POST /admin/groups/{group_id}/members
Add multiple students to group

**Request:**
```json
{
  "profile_ids": [123, 124, 125]
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Added 3 members to group"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Group not found"
}
```

### GET /admin/groups/{group_id}/members
Get all members in group

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": [
    {
      "profile_id": 123,
      "full_name": "John Doe",
      "joined_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Group not found"
}
```

### POST /admin/groups/{group_id}/members/{profile_id}
Add individual student to group

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Student added to group successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Group not found"
}
```

```json
{
  "success": false,
  "detail": "Student not found"
}
```

```json
{
  "success": false,
  "detail": "Student already in group"
}
```

### DELETE /admin/groups/{group_id}/members/{profile_id}
Remove student from group

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Student removed from group successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Group not found"
}
```

```json
{
  "success": false,
  "detail": "Student not in group"
}
```

## Course Management

### POST /admin/courses
Create new course

**Request:**
```json
{
  "title": "English Fundamentals",
  "description": "Basic English language course"
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "course_id": 1,
    "message": "Course created successfully"
  }
}
```

### GET /admin/courses
Get all courses in center

**Request:** None

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

### PUT /admin/courses/{course_id}
Update course

**Request:**
```json
{
  "title": "Updated Course Title",
  "description": "Updated course description"
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Course updated successfully"
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

### DELETE /admin/courses/{course_id}
Soft delete course

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Course deleted successfully"
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

### POST /admin/courses/{course_id}/modules
Create new module in course

**Request:**
```json
{
  "title": "Grammar Basics",
  "description": "Introduction to English grammar",
  "order_index": 1
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "module_id": 10,
    "message": "Module created successfully"
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

### GET /admin/courses/{course_id}/modules
Get all modules in course

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": [
    {
      "id": 10,
      "title": "Grammar Basics",
      "description": "Introduction to English grammar",
      "order_index": 1,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Course not found"
}
```

### PUT /admin/modules/{module_id}
Update module

**Request:**
```json
{
  "title": "Updated Module Title",
  "description": "Updated module description",
  "order_index": 2
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Module updated successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Module not found"
}
```

### DELETE /admin/modules/{module_id}
Soft delete module

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Module deleted successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Module not found"
}
```

## Lesson Management

### POST /admin/modules/{module_id}/lessons
Create new lesson in module

**Request:**
```json
{
  "title": "Present Tense",
  "description": "Learning present tense verbs",
  "order_index": 1
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "lesson_id": 20,
    "message": "Lesson created successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Module not found"
}
```

### GET /admin/modules/{module_id}/lessons
Get all lessons in module

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": [
    {
      "id": 20,
      "title": "Present Tense",
      "description": "Learning present tense verbs",
      "order_index": 1,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Module not found"
}
```

### PUT /admin/lessons/{lesson_id}
Update lesson

**Request:**
```json
{
  "title": "Updated Lesson Title",
  "description": "Updated lesson description",
  "order_index": 2
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Lesson updated successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Lesson not found"
}
```

### DELETE /admin/lessons/{lesson_id}
Soft delete lesson

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Lesson deleted successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Lesson not found"
}
```

## Word Management

### POST /admin/lessons/{lesson_id}/words
Add word to lesson

**Request:**
```json
{
  "word": "apple",
  "meaning": "olma",
  "definition": "A round fruit with red or green skin",
  "example_sentence": "I eat an apple every day",
  "image_url": "https://example.com/apple.jpg",
  "audio_url": "https://example.com/apple.mp3",
  "order_index": 1
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "word_id": 30,
    "message": "Word added successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Lesson not found"
}
```

### POST /admin/lessons/{lesson_id}/words/bulk
Add multiple words to lesson

**Request:**
```json
{
  "words": [
    {
      "word": "apple",
      "meaning": "olma",
      "definition": "A round fruit with red or green skin",
      "example_sentence": "I eat an apple every day",
      "order_index": 1
    },
    {
      "word": "banana",
      "meaning": "banan",
      "definition": "A long yellow fruit",
      "example_sentence": "Bananas are yellow",
      "order_index": 2
    }
  ]
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Added 2 words successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Lesson not found"
}
```

### GET /admin/lessons/{lesson_id}/words
Get all words in lesson

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
      "order_index": 1,
      "created_at": "2024-01-15T10:30:00Z"
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

### PUT /admin/words/{word_id}
Update word

**Request:**
```json
{
  "word": "apple",
  "meaning": "updated olma",
  "definition": "Updated definition",
  "example_sentence": "Updated example sentence",
  "order_index": 1
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Word updated successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Word not found"
}
```

### DELETE /admin/words/{word_id}
Soft delete word

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Word deleted successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Word not found"
}
```

### POST /admin/words/{word_id}/image
Upload image for word

**Request:** Multipart form data with image file (PNG, JPG, etc.)

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Word image uploaded successfully",
    "image_url": "/storage/word-images/abc123.jpg"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Word not found"
}
```

```json
{
  "success": false,
  "detail": "File must be an image"
}
```

```json
{
  "success": false,
  "detail": "No file selected"
}
```

### POST /admin/words/{word_id}/audio
Upload audio for word (max 7 seconds, 1MB)

**Request:** Multipart form data with audio file (MP3, WAV, etc.)

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Word audio uploaded successfully",
    "audio_url": "/storage/word-audio/def456.mp3"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Audio duration must be 7 seconds or less"
}
```

```json
{
  "success": false,
  "detail": "Audio size must be less than 1MB"
}
```

## Password Management

### PATCH /admin/password
Change admin user password

**Request:**
```json
{
  "new_password": "newSecurePassword123"
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Password updated successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Admin user not found"
}
```

## Analytics

### GET /admin/analytics/overview
Get learning center analytics overview

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "total_lessons": 150,
    "completed_lessons": 75,
    "completion_rate": 50.0,
    "top_students": [
      {
        "profile_id": 123,
        "full_name": "John Doe",
        "total_coins": 1250,
        "avatar": "/storage/avatars/user123.jpg"
      }
    ]
  }
}
```

## Payment History

### GET /admin/payments
Get payment history for center

**Request Parameters:**
- `page` (int, optional): Page number (default: 1)
- `size` (int, optional): Items per page (default: 20)

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 789,
        "amount": 500.00,
        "days_added": 30,
        "description": "Monthly subscription payment",
        "created_at": "2024-01-15T10:30:00Z"
      }
    ],
    "total": 10,
    "page": 1,
    "size": 20
  }
}
```

## Learning Center Management

### GET /admin/center/info
Get basic learning center information

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "title": "English Learning Hub",
    "logo": "/storage/logos/center1.png",
    "student_limit": 100,
    "days_remaining": 25,
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Center not found"
}
```

### PATCH /admin/center
Update learning center title

**Request:**
```json
{
  "title": "Updated Learning Center Name"
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Center updated successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Center not found"
}
```

### POST /admin/center/logo
Upload logo for learning center

**Request:** Multipart form data with PNG file (max 3MB)

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Center logo uploaded successfully",
    "logo_url": "/storage/logos/abc123.png"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Center not found"
}
```

```json
{
  "success": false,
  "detail": "Only PNG files are allowed"
}
```

```json
{
  "success": false,
  "detail": "File size must be less than 3MB"
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
  "detail": "Admin access required"
}
```

### Center Inactive
```json
{
  "success": false,
  "detail": "Learning center subscription has expired"
}
```

### No Center Access
```json
{
  "success": false,
  "detail": "No center access"
}
```

### Server Error
```json
{
  "success": false,
  "detail": "Internal server error"
}
```
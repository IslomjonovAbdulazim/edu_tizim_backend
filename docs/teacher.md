# Teacher API Endpoints

**Base URL:** `https://edutizimbackend-production.up.railway.app`

## Authentication
All teacher endpoints require authentication with a JWT token in the Authorization header:
```
Authorization: Bearer <jwt_token>
```

## Dashboard

### GET /teacher/dashboard
Get teacher dashboard with assigned groups overview and recent student activity

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "teacher": {
      "id": 4,
      "full_name": "Jane Smith"
    },
    "stats": {
      "assigned_groups": 3,
      "total_students": 45
    },
    "groups": [
      {
        "id": 1,
        "name": "Beginner English A1",
        "course_id": 1,
        "created_at": "2024-01-15T10:30:00Z"
      }
    ],
    "recent_activity": [
      {
        "lesson_id": 5,
        "percentage": 85,
        "completed": true,
        "last_practiced": "2024-01-20T14:30:00Z"
      }
    ]
  }
}
```

## Group Management

### GET /teacher/groups
Get all groups assigned to the teacher

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Beginner English A1",
      "course_id": 1,
      "student_count": 15,
      "created_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": 2,
      "name": "Intermediate English B1",
      "course_id": 2,
      "student_count": 12,
      "created_at": "2024-01-16T09:00:00Z"
    }
  ]
}
```

### GET /teacher/groups/{group_id}/students
Get students in a specific group with progress and ranking

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "group": {
      "id": 1,
      "name": "Beginner English A1",
      "course_id": 1
    },
    "students": [
      {
        "profile": {
          "id": 6,
          "full_name": "Abduazim",
          "created_at": "2025-08-31T16:52:04.928963"
        },
        "progress": {
          "completed_lessons": 5,
          "total_lessons": 10,
          "average_percentage": 78.5,
          "total_coins": 150,
          "total_points": 150
        },
        "rank": 1
      },
      {
        "profile": {
          "id": 7,
          "full_name": "Sarah Johnson",
          "created_at": "2025-08-30T14:20:00.000000"
        },
        "progress": {
          "completed_lessons": 3,
          "total_lessons": 8,
          "average_percentage": 65.2,
          "total_coins": 120,
          "total_points": 120
        },
        "rank": 2
      }
    ]
  }
}
```

**Response (Error - Unauthorized):**
```json
{
  "success": false,
  "detail": "Not authorized for this group"
}
```

### GET /teacher/groups/{group_id}/leaderboard
Get leaderboard for a specific group

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "group": {
      "id": 1,
      "name": "Beginner English A1"
    },
    "leaderboard": [
      {
        "rank": 1,
        "profile_id": 6,
        "full_name": "Abduazim",
        "total_coins": 150,
        "avatar": "/storage/avatars/user6.jpg"
      },
      {
        "rank": 2,
        "profile_id": 7,
        "full_name": "Sarah Johnson",
        "total_coins": 120,
        "avatar": null
      }
    ]
  }
}
```

**Response (Error - Unauthorized):**
```json
{
  "success": false,
  "detail": "Not authorized for this group"
}
```

## Student Progress Tracking

### GET /teacher/students/{student_id}/progress
Get detailed progress for a specific student

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "student": {
      "id": 6,
      "full_name": "Abduazim",
      "created_at": "2025-08-31T16:52:04.928963"
    },
    "progress": [
      {
        "lesson_id": 1,
        "percentage": 100,
        "completed": true,
        "last_practiced": "2024-01-20T14:30:00Z"
      },
      {
        "lesson_id": 2,
        "percentage": 75,
        "completed": false,
        "last_practiced": "2024-01-21T10:15:00Z"
      }
    ],
    "weak_words": [
      {
        "word_id": 15,
        "word": "apple",
        "meaning": "olma",
        "last_seven_attempts": "1010110",
        "total_correct": 45,
        "total_attempts": 60
      }
    ],
    "recent_activity": [
      {
        "amount": 10,
        "source": "lesson",
        "earned_at": "2024-01-21T10:15:00Z"
      },
      {
        "amount": 5,
        "source": "revision",
        "earned_at": "2024-01-20T16:45:00Z"
      }
    ]
  }
}
```

**Response (Error - No Access):**
```json
{
  "success": false,
  "detail": "No access to this student"
}
```

**Response (Error - Not Found):**
```json
{
  "success": false,
  "detail": "Student not found"
}
```

### GET /teacher/students/struggling
Get students who need attention (low progress or inactive)

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": [
    {
      "student": {
        "id": 8,
        "full_name": "Mike Wilson"
      },
      "reason": "No progress recorded",
      "avg_percentage": 0
    },
    {
      "student": {
        "id": 9,
        "full_name": "Lisa Chen"
      },
      "reason": "Low completion rate",
      "avg_percentage": 35.5
    },
    {
      "student": {
        "id": 10,
        "full_name": "David Brown"
      },
      "reason": "No recent activity",
      "avg_percentage": 68.2
    }
  ]
}
```

## Analytics

### GET /teacher/analytics/overview
Get analytics overview for teacher's assigned groups

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "total_groups": 3,
    "total_students": 45,
    "active_students": 38,
    "avg_completion_rate": 67.5,
    "completed_lessons": 156,
    "total_lessons": 231
  }
}
```

## Reporting

### GET /teacher/reports/weekly
Get weekly activity report for teacher's groups

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "week_summary": {
      "total_progress_records": 125,
      "daily_breakdown": [
        {
          "date": "2024-01-15",
          "lessons_completed": 8,
          "active_students": 12
        },
        {
          "date": "2024-01-16",
          "lessons_completed": 15,
          "active_students": 18
        },
        {
          "date": "2024-01-17",
          "lessons_completed": 22,
          "active_students": 25
        }
      ]
    }
  }
}
```

## Data Structure Details

### Student Progress Object
```json
{
  "completed_lessons": 5,        // Number of lessons completed (100%)
  "total_lessons": 10,          // Total lessons attempted
  "average_percentage": 78.5,   // Average completion percentage across all lessons
  "total_coins": 150,           // Total coins earned
  "total_points": 150           // Total points (same as total_coins)
}
```

### Ranking System
- Students are automatically ranked by `total_points` in descending order
- Rank 1 = highest points, Rank 2 = second highest, etc.
- Students with the same points share the same rank

### Weak Words Tracking
- `last_seven_attempts`: String of 7 characters (0=incorrect, 1=correct)
- Words appearing in weak words list have at least one '0' in their last seven attempts
- Used to identify words students struggle with

### Activity Sources
- `lesson`: Points earned from completing lessons
- `revision`: Points earned from reviewing previous content
- `bonus`: Points earned from special activities

## Password Management

### PATCH /teacher/password
Change teacher password

**Request:**
```json
{
  "current_password": "oldpassword123",
  "new_password": "newSecurePassword123",
  "confirm_password": "newSecurePassword123"
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
  "detail": "New passwords do not match"
}
```

```json
{
  "success": false,
  "detail": "Current password is incorrect"
}
```

```json
{
  "success": false,
  "detail": "Teacher user not found"
}
```

## Common Error Responses

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
  "detail": "Teacher access required"
}
```

### No Center Access
```json
{
  "success": false,
  "detail": "No center access"
}
```

### Center Inactive
```json
{
  "success": false,
  "detail": "Learning center subscription has expired"
}
```

### Group Not Found/Unauthorized
```json
{
  "success": false,
  "detail": "Not authorized for this group"
}
```

### Student Not Found
```json
{
  "success": false,
  "detail": "Student not found"
}
```

### No Student Access
```json
{
  "success": false,
  "detail": "No access to this student"
}
```

## Usage Examples

### Get students in group with rankings
```bash
curl -X 'GET' \
  'https://edutizimbackend-production.up.railway.app/api/teacher/groups/1/students' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <your_jwt_token>'
```

### Check teacher analytics
```bash
curl -X 'GET' \
  'https://edutizimbackend-production.up.railway.app/api/teacher/analytics/overview' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <your_jwt_token>'
```

### Monitor struggling students
```bash
curl -X 'GET' \
  'https://edutizimbackend-production.up.railway.app/api/teacher/students/struggling' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <your_jwt_token>'
```

## Notes

- All timestamps are in ISO 8601 format with UTC timezone
- Points and coins are interchangeable terms in the system
- Teachers can only access students in their assigned groups
- All responses follow the standard APIResponse format with `success` and `data` fields
- Pagination is not implemented for teacher endpoints as groups typically have manageable student counts
- Students are automatically sorted by points when retrieving group members
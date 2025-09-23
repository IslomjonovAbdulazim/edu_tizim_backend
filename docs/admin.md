# Admin API Documentation

Admin users manage their learning center's users, groups, and content. They have full control within their assigned learning center.

## Authentication

Admins use phone verification like other users:

1. `POST /api/v1/auth/send-code` - Request verification code
2. `POST /api/v1/auth/verify-login` - Login with code

## User Management

### Create User
`POST /api/v1/admin/users`

**Request:**
```json
{
  "phone": "+998901234567",
  "name": "John Teacher",
  "role": "teacher"
}
```

**Response:**
```json
{
  "id": 123,
  "phone": "+998901234567",
  "name": "John Teacher",
  "role": "teacher",
  "coins": 0,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### List Users
`GET /api/v1/admin/users?role=student&skip=0&limit=50`

**Query Parameters:**
- `role` (optional): Filter by role (`admin`, `teacher`, `student`)
- `skip` (optional): Pagination offset (default: 0)
- `limit` (optional): Items per page (default: 100)

**Response:**
```json
[
  {
    "id": 124,
    "phone": "+998901234568",
    "name": "Jane Student",
    "role": "student",
    "coins": 250,
    "is_active": true,
    "created_at": "2024-01-10T09:15:00Z"
  }
]
```

### Update User
`PUT /api/v1/admin/users/123`

**Request:**
```json
{
  "name": "Updated Teacher Name",
  "phone": "+998901234569",
  "role": "teacher"
}
```

**Response:**
```json
{
  "id": 123,
  "phone": "+998901234569",
  "name": "Updated Teacher Name",
  "role": "teacher",
  "coins": 0,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Deactivate User
`DELETE /api/v1/admin/users/123`

**Response:**
```json
{
  "message": "User deactivated successfully"
}
```

## Group Management

### Create Group
`POST /api/v1/admin/groups`

**Request:**
```json
{
  "name": "Beginner English A1",
  "course_id": 1,
  "teacher_id": 123
}
```

**Response:**
```json
{
  "id": 1,
  "name": "Beginner English A1",
  "course_id": 1,
  "teacher_id": 123,
  "student_count": 0,
  "created_at": "2024-01-15T11:00:00Z"
}
```

### List Groups
`GET /api/v1/admin/groups?skip=0&limit=50`

**Response:**
```json
[
  {
    "id": 1,
    "name": "Beginner English A1",
    "course_id": 1,
    "teacher_id": 123,
    "student_count": 15,
    "created_at": "2024-01-15T11:00:00Z"
  }
]
```

### Update Group
`PUT /api/v1/admin/groups/1`

**Request:**
```json
{
  "name": "Updated Group Name",
  "teacher_id": 124,
  "course_id": 2
}
```

**Response:**
```json
{
  "id": 1,
  "name": "Updated Group Name",
  "course_id": 2,
  "teacher_id": 124,
  "student_count": 15,
  "created_at": "2024-01-15T11:00:00Z"
}
```

### Add Student to Group
`POST /api/v1/admin/groups/1/students`

**Request:**
```json
{
  "student_id": 125
}
```

**Response:**
```json
{
  "message": "Student added to group successfully"
}
```

### Remove Student from Group
`DELETE /api/v1/admin/groups/1/students/125`

**Response:**
```json
{
  "message": "Student removed from group successfully"
}
```

### Delete Group
`DELETE /api/v1/admin/groups/1`

**Response:**
```json
{
  "message": "Group deleted successfully"
}
```

## Content Management

Admins have full access to content management endpoints:

### Course Management
- `POST /api/v1/content/courses` - Create course
- `GET /api/v1/content/courses` - List courses
- `PUT /api/v1/content/courses/{id}` - Update course
- `DELETE /api/v1/content/courses/{id}` - Delete course

### Lesson Management
- `POST /api/v1/content/courses/{id}/lessons` - Create lesson
- `GET /api/v1/content/courses/{id}/lessons` - List lessons
- `PUT /api/v1/content/lessons/{id}` - Update lesson
- `DELETE /api/v1/content/lessons/{id}` - Delete lesson

### Word Management
- `POST /api/v1/content/lessons/{id}/words` - Create word
- `GET /api/v1/content/lessons/{id}/words` - List words
- `PUT /api/v1/content/words/{id}` - Update word
- `DELETE /api/v1/content/words/{id}` - Delete word
- `POST /api/v1/content/words/{id}/audio` - Upload audio
- `POST /api/v1/content/words/{id}/image` - Upload image

## Access Control

### Permissions
- **Scoped to learning center**: Can only manage users/content within their center
- **User limits**: Cannot exceed center's student/teacher limits
- **Group limits**: Cannot exceed center's group limit
- **Payment dependent**: Access blocked if center is unpaid

### Validation
- Phone numbers must be unique within the learning center
- Teachers must belong to the same learning center
- Courses must exist and be active
- Students can only be added to groups in the same center

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Phone number already exists in this learning center"
}
```

### 402 Payment Required
```json
{
  "detail": "Learning center subscription expired"
}
```

### 403 Forbidden
```json
{
  "detail": "Not enough permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Teacher not found"
}
```

## Key Features

- **Complete user management**: Create, update, deactivate users
- **Group organization**: Manage classes and assign teachers
- **Content creation**: Build courses, lessons, and vocabulary
- **File uploads**: Add audio and images to words
- **Real-time limits**: Enforced student/teacher/group quotas
- **Cache optimization**: Automatic cache invalidation on updates
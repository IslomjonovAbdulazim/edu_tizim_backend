# Super Admin API Documentation

Super Admin has full control over the entire system, managing all learning centers and their configurations.

## Authentication

### Login
`POST /api/v1/auth/super-admin/login`

**Request:**
```json
{
  "email": "admin@gmail.com",
  "password": "admin123"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 0,
    "email": "admin@gmail.com",
    "role": "super_admin"
  }
}
```

## Learning Center Management

### Create Learning Center
`POST /api/v1/super-admin/learning-centers`

**Request:**
```json
{
  "name": "ABC Learning Center",
  "phone": "+998901234567",
  "student_limit": 500,
  "teacher_limit": 50,
  "group_limit": 100,
  "is_paid": true
}
```

**Response:**
```json
{
  "id": 1,
  "name": "ABC Learning Center",
  "logo": null,
  "phone": "+998901234567",
  "student_limit": 500,
  "teacher_limit": 50,
  "group_limit": 100,
  "is_active": true,
  "is_paid": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### List All Learning Centers
`GET /api/v1/super-admin/learning-centers?skip=0&limit=100`

**Response:**
```json
[
  {
    "id": 1,
    "name": "ABC Learning Center",
    "logo": "logos/center_1_uuid.png",
    "phone": "+998901234567",
    "student_limit": 500,
    "teacher_limit": 50,
    "group_limit": 100,
    "is_active": true,
    "is_paid": true,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

### Update Learning Center
`PUT /api/v1/super-admin/learning-centers/1`

**Request:**
```json
{
  "name": "Updated Learning Center Name",
  "student_limit": 1000,
  "is_paid": false
}
```

**Response:**
```json
{
  "id": 1,
  "name": "Updated Learning Center Name",
  "logo": "logos/center_1_uuid.png",
  "phone": "+998901234567",
  "student_limit": 1000,
  "teacher_limit": 50,
  "group_limit": 100,
  "is_active": true,
  "is_paid": false,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Upload Learning Center Logo
`POST /api/v1/super-admin/learning-centers/1/logo`

**Request:**
- Content-Type: `multipart/form-data`
- Form field: `file` (image file)

**Response:**
```json
{
  "message": "Logo uploaded successfully",
  "path": "logos/center_1_abc123.png"
}
```

### Toggle Payment Status
`POST /api/v1/super-admin/learning-centers/1/toggle-payment`

**Response:**
```json
{
  "message": "Payment status disabled",
  "is_paid": false
}
```

### Deactivate Learning Center
`DELETE /api/v1/super-admin/learning-centers/1`

**Response:**
```json
{
  "message": "Learning center deactivated successfully"
}
```

## User Management

Super admins can create and manage users (admins, teachers, students) across all learning centers:

### Create User (Admin/Teacher/Student)
`POST /api/v1/super-admin/users`

**Request:**
```json
{
  "phone": "+998901234567",
  "name": "John Admin",
  "role": "admin",
  "learning_center_id": 1
}
```

**Response:**
```json
{
  "id": 123,
  "phone": "+998901234567",
  "name": "John Admin",
  "role": "admin",
  "learning_center_id": 1,
  "coins": 0,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### List All Users
`GET /api/v1/super-admin/users?learning_center_id=1&role=admin&skip=0&limit=100`

**Query Parameters:**
- `learning_center_id` (optional): Filter by learning center
- `role` (optional): Filter by role (admin, teacher, student)
- `skip` (optional): Pagination offset
- `limit` (optional): Items per page

**Response:**
```json
[
  {
    "id": 123,
    "phone": "+998901234567",
    "name": "John Admin",
    "role": "admin",
    "learning_center_id": 1,
    "coins": 0,
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

### Get Specific User
`GET /api/v1/super-admin/users/123`

**Response:**
```json
{
  "id": 123,
  "phone": "+998901234567",
  "name": "John Admin",
  "role": "admin",
  "learning_center_id": 1,
  "coins": 0,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Update User
`PUT /api/v1/super-admin/users/123`

**Request:**
```json
{
  "name": "Updated Admin Name",
  "phone": "+998901234568",
  "role": "admin",
  "learning_center_id": 2
}
```

**Response:**
```json
{
  "id": 123,
  "phone": "+998901234568",
  "name": "Updated Admin Name",
  "role": "admin",
  "learning_center_id": 2,
  "coins": 0,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Delete User
`DELETE /api/v1/super-admin/users/123`

**Response:**
```json
{
  "message": "User deleted successfully"
}
```

## Typical Workflow

### Setting up a New Learning Center

1. **Create Learning Center**
```json
POST /api/v1/super-admin/learning-centers
{
  "name": "New Learning Center",
  "phone": "+998901234567",
  "student_limit": 500,
  "teacher_limit": 50,
  "group_limit": 100,
  "is_paid": true
}
```

2. **Create Admin for the Center**
```json
POST /api/v1/super-admin/users
{
  "phone": "+998901234568",
  "name": "Center Admin",
  "role": "admin",
  "learning_center_id": 1
}
```
 
## Content Management (Full Access)

Super admins have **exclusive full access** to all content management operations across all learning centers:

### Course Management
- `POST /api/v1/super-admin/content/courses` - Create course
- `GET /api/v1/super-admin/content/courses` - List all courses across centers
- `PUT /api/v1/super-admin/content/courses/{id}` - Update course
- `DELETE /api/v1/super-admin/content/courses/{id}` - Delete course

### Lesson Management
- `POST /api/v1/super-admin/content/courses/{id}/lessons` - Create lesson
- `GET /api/v1/super-admin/content/lessons` - List all lessons
- `PUT /api/v1/super-admin/content/lessons/{id}` - Update lesson
- `DELETE /api/v1/super-admin/content/lessons/{id}` - Delete lesson

### Word Management
- `POST /api/v1/super-admin/content/lessons/{id}/words` - Create word
- `GET /api/v1/super-admin/content/words` - List all words
- `PUT /api/v1/super-admin/content/words/{id}` - Update word
- `DELETE /api/v1/super-admin/content/words/{id}` - Delete word
- `POST /api/v1/super-admin/content/words/{id}/audio` - Upload audio files
- `POST /api/v1/super-admin/content/words/{id}/image` - Upload images

### Content Management Examples

**Create Course:**
```json
POST /api/v1/super-admin/content/courses
{
  "title": "English Basics",
  "learning_center_id": 1
}
```

**Create Lesson:**
```json
POST /api/v1/super-admin/content/courses/1/lessons
{
  "title": "Greetings",
  "content": "Learn basic greetings",
  "order": 1
}
```

**Create Word:**
```json
POST /api/v1/super-admin/content/lessons/1/words
{
  "word": "hello",
  "translation": "salom",
  "definition": "A greeting",
  "sentence": "Hello, how are you?",
  "difficulty": "easy",
  "order": 1
}
```

**Note**: Only Super Admin can create, edit, or delete content. Other roles have read-only access to content within their learning center scope.

## Key Features

- **System-wide control**: Manage all learning centers
- **Payment control**: Enable/disable center subscriptions
- **Billing management**: Track usage and enforce limits
- **Content oversight**: Access to all educational content
- **User analytics**: View system-wide statistics

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Invalid super admin credentials"
}
```

### 404 Not Found
```json
{
  "detail": "Learning center not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error message"
}
```

## Notes

- Super admin credentials are stored in environment variables
- Only one super admin exists in the system
- All operations automatically invalidate relevant caches
- Payment status changes immediately affect center access
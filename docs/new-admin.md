# Admin API Documentation

Admin users manage their learning center's users, groups, and have read-only access to content. All operations are scoped to their assigned learning center with proper soft delete support.

## Authentication

Admins use standard phone verification with learning center scoping:

### Get Available Learning Centers (Public)
`GET /api/v1/auth/learning-centers`

**Description:** Public endpoint to fetch all active learning centers for dropdown selection.

**Response:**
```json
[
  {
    "id": 1,
    "name": "ABC Learning Center",
    "logo": "logos/center_1_uuid.png"
  },
  {
    "id": 2,
    "name": "XYZ Learning Center", 
    "logo": null
  }
]
```

### Send Verification Code
`POST /api/v1/auth/send-code`

**Request:**
```json
{
  "phone": "+998901234567",
  "learning_center_id": 1
}
```

**Response:**
```json
{
  "message": "Verification code sent successfully"
}
```

### Verify Code and Login
`POST /api/v1/auth/verify-login`

**Request:**
```json
{
  "phone": "+998901234567",
  "code": "123456",
  "learning_center_id": 1
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 123,
    "phone": "+998901234567",
    "name": "John Admin",
    "role": "admin",
    "learning_center_id": 1,
    "coins": 0
  }
}

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

**Restrictions:**
- Can only create `teacher` and `student` roles
- Admin accounts can only be created by Super Admin
- Phone must be unique within the learning center

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

### Get User
`GET /api/v1/admin/users/124`

**Response:**
```json
{
  "id": 124,
  "phone": "+998901234568",
  "name": "Jane Student",
  "role": "student",
  "coins": 250,
  "is_active": true,
  "created_at": "2024-01-10T09:15:00Z"
}
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

**Restrictions:**
- Cannot change role to `admin`
- Phone must be unique within learning center
- User must belong to same learning center

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

### Delete User (Soft Delete)
`DELETE /api/v1/admin/users/123`

**Features:**
- Soft delete: Sets `deleted_at` timestamp and `is_active = false`
- Preserves data for audit purposes
- User cannot be retrieved in future queries

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

**Validations:**
- Teacher must exist, be active, and belong to same learning center
- Course must exist, be active, and belong to same learning center
- Excludes soft-deleted records

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

**Query Parameters:**
- `skip` (optional): Pagination offset
- `limit` (optional): Items per page

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

### Get Group
`GET /api/v1/admin/groups/1`

**Response:**
```json
{
  "id": 1,
  "name": "Beginner English A1",
  "course_id": 1,
  "teacher_id": 123,
  "student_count": 15,
  "created_at": "2024-01-15T11:00:00Z"
}
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

**Validations:**
- New teacher must exist, be active, and belong to same learning center
- New course must exist, be active, and belong to same learning center
- Excludes soft-deleted records

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

**Validations:**
- Student must belong to same learning center
- Group must belong to same learning center
- Student cannot be added to group twice

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

### Delete Group (Soft Delete)
`DELETE /api/v1/admin/groups/1`

**Features:**
- Soft delete: Sets `deleted_at` timestamp
- Group relationships preserved
- Cannot be retrieved in future queries

**Response:**
```json
{
  "message": "Group deleted successfully"
}
```

## Content Access (Read-Only)

Admins have **read-only access** to view content within their learning center.

### View Courses
`GET /api/v1/content/courses`

Lists courses available in the admin's learning center.

### View Course Lessons
`GET /api/v1/content/courses/{id}/lessons`

Lists lessons for a specific course.

### View Lesson Words
`GET /api/v1/content/lessons/{id}/words`

Lists vocabulary words for a specific lesson.

**Note:** Content creation, editing, and deletion is restricted to Super Admin only.

## Access Control & Validation

### Learning Center Scoping
- All operations limited to admin's assigned learning center
- Cannot access or modify data from other learning centers
- All queries include learning center filter

### Soft Delete Support
- All queries exclude records with `deleted_at != NULL`
- Deleted records preserved for audit purposes
- Consistent implementation across all endpoints

### Role Restrictions
- Cannot create admin accounts (Super Admin only)
- Cannot change user roles to admin
- Can only assign teacher/student roles

### Resource Limits
- Respects learning center's user limits
- Cannot exceed student/teacher/group quotas
- Payment status affects access

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
  "detail": "Admin accounts can only be created by Super Admin"
}
```

### 404 Not Found
```json
{
  "detail": "Teacher not found"
}
```

## Key Features

- **Learning Center Scoped**: All operations limited to admin's center
- **Soft Delete Enabled**: Proper data preservation and audit trails
- **Role Management**: Create and manage teachers/students
- **Group Organization**: Full group lifecycle management
- **Content Viewing**: Read-only access to educational content
- **Validation**: Comprehensive data integrity checks
- **Phone Uniqueness**: Enforced within learning center scope
- **Resource Quotas**: Automatic limit enforcement
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
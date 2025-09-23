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

## Content Management Access

Super admins have full access to all content management endpoints for any learning center:

- All course management endpoints (`/api/v1/content/courses`)
- All lesson management endpoints (`/api/v1/content/lessons`)
- All word management endpoints (`/api/v1/content/words`)

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
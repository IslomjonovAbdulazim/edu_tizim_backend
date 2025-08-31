# Super Admin API Endpoints

**Base URL:** `https://edutizimbackend-production.up.railway.app`

## Dashboard

### GET /super-admin/dashboard
Get system overview dashboard

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "stats": {
      "total_centers": 25,
      "active_centers": 20,
      "total_students": 1250,
      "total_teachers": 85,
      "total_revenue": 15000.50
    },
    "recent_centers": [
      {
        "id": 123,
        "title": "English Learning Hub",
        "days_remaining": 25,
        "is_active": true,
        "created_at": "2024-01-15T10:30:00Z"
      }
    ],
    "expiring_centers": [
      {
        "id": 124,
        "title": "Math Academy",
        "days_remaining": 3,
        "owner_id": 456
      }
    ]
  }
}
```

## Learning Centers Management

### POST /super-admin/centers
Create new learning center and admin user

**Request:**
```json
{
  "title": "New Learning Center",
  "logo": "https://example.com/logo.png",
  "student_limit": 100,
  "owner_email": "admin@center.com",
  "owner_password": "securepassword123"
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "center_id": 123,
    "admin_user_id": 456,
    "message": "Learning center and admin created successfully"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Admin email already exists"
}
```

### GET /super-admin/centers
Get all learning centers with pagination and filtering

**Request Parameters:**
- `page` (int, optional): Page number (default: 1)
- `size` (int, optional): Items per page (default: 20)
- `search` (string, optional): Search by center title
- `status_filter` (string, optional): "active", "inactive", "expiring"

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 123,
        "title": "English Learning Hub",
        "logo": "https://example.com/logo.png",
        "days_remaining": 25,
        "student_limit": 100,
        "student_count": 75,
        "is_active": true,
        "owner_id": 456,
        "created_at": "2024-01-15T10:30:00Z"
      }
    ],
    "total": 50,
    "page": 1,
    "size": 20
  }
}
```

### GET /super-admin/centers/{center_id}
Get detailed center information

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "center": {
      "id": 123,
      "title": "English Learning Hub",
      "logo": "https://example.com/logo.png",
      "days_remaining": 25,
      "student_limit": 100,
      "is_active": true,
      "owner_id": 456,
      "created_at": "2024-01-15T10:30:00Z"
    },
    "stats": {
      "total_students": 75,
      "total_teachers": 5,
      "total_courses": 3,
      "total_lessons": 150
    },
    "recent_payments": [
      {
        "id": 789,
        "amount": 500.00,
        "days_added": 30,
        "description": "Monthly subscription",
        "created_at": "2024-01-15T10:30:00Z"
      }
    ]
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

### PATCH /super-admin/centers/{center_id}/status
Activate/deactivate learning center

**Request:**
```json
{
  "is_active": true
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Center activated successfully",
    "center_id": 123,
    "is_active": true
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Cannot activate center with 0 days remaining. Add payment first."
}
```

### PATCH /super-admin/centers/{center_id}/extend
Extend center subscription without payment (admin override)

**Request:**
```json
{
  "days": 30,
  "reason": "Trial extension"
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Extended center by 30 days",
    "new_days_remaining": 55
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "detail": "Days must be greater than 0"
}
```

### DELETE /super-admin/centers/{center_id}
Soft delete learning center

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Center deleted successfully"
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

## Payment Management

### POST /super-admin/payments
Add payment and extend center subscription

**Request:**
```json
{
  "center_id": 123,
  "amount": 500.00,
  "days_added": 30,
  "description": "Monthly subscription payment"
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "payment_id": 789,
    "message": "Payment processed successfully. Added 30 days.",
    "new_days_remaining": 55
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

### GET /super-admin/payments
Get payment history with filtering

**Request Parameters:**
- `center_id` (int, optional): Filter by center ID
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
        "center_id": 123,
        "center_title": "English Learning Hub",
        "amount": 500.00,
        "days_added": 30,
        "description": "Monthly subscription payment",
        "created_at": "2024-01-15T10:30:00Z"
      }
    ],
    "total": 100,
    "page": 1,
    "size": 20
  }
}
```

## System Analytics

### GET /super-admin/analytics/revenue
Get revenue analytics by period

**Request Parameters:**
- `period` (string, optional): "weekly", "monthly", "yearly" (default: "monthly")

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "period": "monthly",
    "revenue_data": [
      {
        "period": "2024-01",
        "revenue": 15000.50
      },
      {
        "period": "2024-02",
        "revenue": 18500.75
      }
    ],
    "total_revenue": 33501.25
  }
}
```

### GET /super-admin/analytics/centers
Get center growth and usage analytics

**Request:** None

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "center_growth": [
      {
        "month": "2024-01-01 00:00:00",
        "count": 5
      },
      {
        "month": "2024-02-01 00:00:00",
        "count": 8
      }
    ],
    "status_distribution": {
      "active": 20,
      "inactive": 5
    },
    "student_distribution": [
      {
        "center": "English Learning Hub",
        "students": 75
      },
      {
        "center": "Math Academy",
        "students": 60
      }
    ]
  }
}
```

## Password Management

### PATCH /super-admin/centers/{center_id}/password
Change learning center admin password

**Request:**
```json
{
  "center_id": 123,
  "new_password": "newSecurePassword123"
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "message": "Center admin password updated successfully"
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
  "detail": "Center admin not found"
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
  "detail": "Super admin access required"
}
```

### Server Error
```json
{
  "success": false,
  "detail": "Internal server error"
}
```
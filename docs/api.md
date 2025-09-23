# API Documentation

## Public Endpoints
`GET /api/v1/auth/learning-centers` - Get all active learning centers for dropdown selection

## Authentication
`POST /api/v1/auth/send-code` - Send SMS verification code to user's phone
`POST /api/v1/auth/verify-login` - Verify SMS code and login user
`POST /api/v1/auth/refresh` - Get new access token using refresh token
`POST /api/v1/auth/super-admin/login` - Login super admin with email/password

## Super Admin
`POST /api/v1/super-admin/learning-centers` - Create new learning center
`GET /api/v1/super-admin/learning-centers` - List all learning centers
`PUT /api/v1/super-admin/learning-centers/{id}` - Update learning center details
`POST /api/v1/super-admin/learning-centers/{id}/logo` - Upload logo for learning center
`POST /api/v1/super-admin/learning-centers/{id}/toggle-payment` - Toggle payment status
`DELETE /api/v1/super-admin/learning-centers/{id}` - Deactivate learning center

## Admin - User Management
`POST /api/v1/admin/users` - Create new user (student/teacher) in learning center
`GET /api/v1/admin/users` - List users in learning center with optional role filter
`PUT /api/v1/admin/users/{id}` - Update user details (phone, name, role)
`DELETE /api/v1/admin/users/{id}` - Deactivate user (soft delete)

## Admin - Group Management
`POST /api/v1/admin/groups` - Create new group with teacher and course
`GET /api/v1/admin/groups` - List all groups in learning center
`PUT /api/v1/admin/groups/{id}` - Update group details (name, teacher, course)
`POST /api/v1/admin/groups/{group_id}/students` - Add student to group
`DELETE /api/v1/admin/groups/{group_id}/students/{student_id}` - Remove student from group
`DELETE /api/v1/admin/groups/{id}` - Delete group (soft delete)

## Teacher
`GET /api/v1/teacher/my-groups` - Get groups assigned to teacher
`GET /api/v1/teacher/groups/{id}/students` - Get students in group with progress

## Student
`GET /api/v1/student/courses` - Get courses available to student
`GET /api/v1/student/courses/{id}/lessons` - Get lessons in course (student view)
`GET /api/v1/student/lessons/{id}/words` - Get words in lesson (student view)
`GET /api/v1/student/progress` - Get student's learning progress and total coins
`POST /api/v1/student/lessons/{id}/complete` - Complete lesson and award coins for improvement
`GET /api/v1/student/leaderboard` - Get learning center leaderboard rankings

## Content Management (Admin/Super Admin)
`POST /api/v1/content/courses` - Create new course in learning center
`PUT /api/v1/content/courses/{id}` - Update course details
`DELETE /api/v1/content/courses/{id}` - Delete course (soft delete)
`GET /api/v1/content/courses` - List all courses in learning center

`POST /api/v1/content/courses/{id}/lessons` - Create lesson in course
`PUT /api/v1/content/lessons/{id}` - Update lesson details
`DELETE /api/v1/content/lessons/{id}` - Delete lesson (soft delete)
`GET /api/v1/content/courses/{id}/lessons` - List lessons in course ordered by sequence

`POST /api/v1/content/lessons/{id}/words` - Create word in lesson with translation and difficulty
`PUT /api/v1/content/words/{id}` - Update word details
`DELETE /api/v1/content/words/{id}` - Delete word (soft delete)
`GET /api/v1/content/lessons/{id}/words` - List words in lesson ordered by sequence

`POST /api/v1/content/words/{id}/audio` - Upload audio file for word pronunciation
`POST /api/v1/content/words/{id}/image` - Upload image file for word visualization

## Error Codes
- **402 Payment Required** - Learning center subscription expired (unpaid status)
- **401 Unauthorized** - Invalid or expired token
- **403 Forbidden** - Insufficient permissions for role
- **404 Not Found** - Resource not found
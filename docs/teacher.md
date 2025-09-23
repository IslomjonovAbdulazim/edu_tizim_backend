# Teacher API Documentation

Teachers can view their assigned groups, monitor student progress, and track learning analytics. They have read-only access to manage their classes.

## Authentication

Teachers use phone verification:

1. `POST /api/v1/auth/send-code` - Request verification code
2. `POST /api/v1/auth/verify-login` - Login with code

## Group Management

### Get My Groups
`GET /api/v1/teacher/my-groups`

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
  },
  {
    "id": 2,
    "name": "Intermediate English B1",
    "course_id": 2,
    "teacher_id": 123,
    "student_count": 12,
    "created_at": "2024-01-10T14:30:00Z"
  }
]
```

### Get Group Students with Progress
`GET /api/v1/teacher/groups/1/students`

**Response:**
```json
{
  "group": {
    "id": 1,
    "name": "Beginner English A1",
    "course_id": 1,
    "student_count": 15
  },
  "students": [
    {
      "id": 125,
      "name": "Alice Student",
      "phone": "+998901234569",
      "coins": 350,
      "progress": {
        "completed_lessons": 5,
        "total_lessons": 10,
        "average_score": 87,
        "total_attempts": 12,
        "last_activity": "2024-01-15T16:45:00Z"
      }
    },
    {
      "id": 126,
      "name": "Bob Student",
      "phone": "+998901234570",
      "coins": 280,
      "progress": {
        "completed_lessons": 3,
        "total_lessons": 10,
        "average_score": 73,
        "total_attempts": 8,
        "last_activity": "2024-01-14T19:20:00Z"
      }
    }
  ]
}
```

## Student Analytics

### Individual Student Progress
Teachers can view detailed progress for each student in their groups:

**Student Performance Metrics:**
- **Completion Rate**: Percentage of lessons completed
- **Average Score**: Mean score across all attempts
- **Learning Velocity**: Lessons completed per week
- **Engagement**: Total attempts and time spent
- **Difficulty Areas**: Words/topics with low success rates

### Group Analytics
Teachers can analyze group performance:

**Group Performance Metrics:**
- **Class Average**: Mean scores across all students
- **Progress Distribution**: How many students at each level
- **Engagement Metrics**: Active vs inactive students
- **Common Challenges**: Words/lessons where students struggle

## Content Access

### View Course Content
Teachers can view the content their groups are studying:

`GET /api/v1/content/courses/{course_id}/lessons`
`GET /api/v1/content/lessons/{lesson_id}/words`

**Use Cases:**
- **Lesson Planning**: Review upcoming content
- **Progress Tracking**: See what students have covered
- **Support Planning**: Identify difficult concepts
- **Assessment Preparation**: Know what to test

## Real-time Monitoring

### Student Activity Tracking
Teachers can monitor:
- **Live Progress**: Students currently studying
- **Recent Completions**: Latest lesson attempts
- **Streak Tracking**: Consecutive study days
- **Coin Earnings**: Gamification progress

### Intervention Opportunities
- **Struggling Students**: Low scores or no recent activity
- **Fast Learners**: Students who need advanced content
- **Engagement Issues**: Students with declining participation

## Reporting & Insights

### Weekly Reports
Automatic insights on:
- **Group Progress**: Overall advancement
- **Individual Highlights**: Top performers and those needing help
- **Content Effectiveness**: Which lessons work well
- **Engagement Trends**: Peak study times and patterns

### Lesson-Level Analytics
- **Completion Rates**: How many students finish each lesson
- **Score Distributions**: Grade spreads across the class
- **Time Analysis**: How long lessons take
- **Retry Patterns**: Which content needs multiple attempts

## Access Control

### Permissions
- **View Only**: Cannot modify students or content
- **Group Scoped**: Only see assigned groups
- **Learning Center Bound**: Cannot access other centers
- **Payment Dependent**: Access blocked if center unpaid

### Data Privacy
- **Student Privacy**: Only see academic progress, not personal details
- **Secure Access**: All data requires authentication
- **Audit Trail**: Teacher access is logged

## Error Responses

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
  "detail": "Group not found"
}
```

## Best Practices

### Student Support
- **Regular Check-ins**: Monitor weekly progress reports
- **Early Intervention**: Contact struggling students quickly
- **Celebrate Success**: Acknowledge high performers
- **Personalized Help**: Use analytics to target support

### Teaching Optimization
- **Content Review**: Analyze which lessons need improvement
- **Pacing Adjustment**: Use completion data to set realistic timelines
- **Engagement Strategies**: Identify when students are most active
- **Differentiation**: Use performance data to group students

## Key Features

- **Real-time dashboard**: Live view of student progress
- **Performance analytics**: Detailed insights into learning patterns
- **Group management**: Overview of all assigned classes
- **Progress tracking**: Monitor individual and group advancement
- **Intervention alerts**: Identify students needing support
- **Content insights**: Understand which materials work best
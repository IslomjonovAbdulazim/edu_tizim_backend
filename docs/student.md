# Student API Documentation

Students can browse learning content, complete lessons, earn coins, and track their progress through gamified learning experiences.

## Authentication

Students use phone verification:

1. `POST /api/v1/auth/send-code` - Request verification code
2. `POST /api/v1/auth/verify-login` - Login with code

## Learning Content

### Get Available Courses
`GET /api/v1/student/courses`

**Response:**
```json
[
  {
    "id": 1,
    "title": "English Basics",
    "learning_center_id": 1,
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "progress": {
      "completed_lessons": 3,
      "total_lessons": 10,
      "completion_percentage": 30
    }
  },
  {
    "id": 2,
    "title": "Advanced English",
    "learning_center_id": 1,
    "is_active": true,
    "created_at": "2024-01-05T00:00:00Z",
    "progress": {
      "completed_lessons": 0,
      "total_lessons": 8,
      "completion_percentage": 0
    }
  }
]
```

### Get Course Lessons
`GET /api/v1/student/courses/1/lessons`

**Response:**
```json
[
  {
    "id": 1,
    "title": "Greetings",
    "content": "Learn basic greetings in English",
    "order": 1,
    "course_id": 1,
    "created_at": "2024-01-01T00:00:00Z",
    "status": "completed",
    "best_score": 85,
    "attempts": 2,
    "coins_earned": 85
  },
  {
    "id": 2,
    "title": "Numbers",
    "content": "Learn numbers 1-10",
    "order": 2,
    "course_id": 1,
    "created_at": "2024-01-01T00:00:00Z",
    "status": "in_progress",
    "best_score": 65,
    "attempts": 1,
    "coins_earned": 65
  },
  {
    "id": 3,
    "title": "Colors",
    "content": "Learn basic colors",
    "order": 3,
    "course_id": 1,
    "created_at": "2024-01-01T00:00:00Z",
    "status": "locked",
    "best_score": 0,
    "attempts": 0,
    "coins_earned": 0
  }
]
```

### Get Lesson Words
`GET /api/v1/student/lessons/1/words`

**Response:**
```json
[
  {
    "id": 1,
    "word": "hello",
    "translation": "salom",
    "definition": "A greeting",
    "sentence": "Hello, how are you?",
    "difficulty": "easy",
    "audio": "audio/word_1_abc123.mp3",
    "image": "images/word_1_def456.jpg",
    "lesson_id": 1,
    "order": 1,
    "created_at": "2024-01-01T00:00:00Z",
    "my_progress": {
      "attempts": 3,
      "correct_attempts": 2,
      "success_rate": 67,
      "last_attempt": "2024-01-15T14:30:00Z"
    }
  },
  {
    "id": 2,
    "word": "goodbye",
    "translation": "xayr",
    "definition": "A farewell",
    "sentence": "Goodbye, see you later!",
    "difficulty": "easy",
    "audio": "audio/word_2_ghi789.mp3",
    "image": "images/word_2_jkl012.jpg",
    "lesson_id": 1,
    "order": 2,
    "created_at": "2024-01-01T00:00:00Z",
    "my_progress": {
      "attempts": 1,
      "correct_attempts": 1,
      "success_rate": 100,
      "last_attempt": "2024-01-15T14:35:00Z"
    }
  }
]
```

## Progress Tracking

### Get My Progress
`GET /api/v1/student/progress`

**Response:**
```json
{
  "summary": {
    "total_coins": 450,
    "lessons_completed": 5,
    "lessons_in_progress": 2,
    "total_lessons": 18,
    "overall_completion": 28,
    "average_score": 82,
    "study_streak": 7,
    "rank_in_center": 3
  },
  "lesson_progress": [
    {
      "lesson_id": 1,
      "lesson_title": "Greetings",
      "best_score": 85,
      "total_coins_earned": 85,
      "lesson_attempts": 2,
      "completed_at": "2024-01-15T14:45:00Z",
      "words_mastered": 8,
      "words_total": 10
    },
    {
      "lesson_id": 2,
      "lesson_title": "Numbers",
      "best_score": 65,
      "total_coins_earned": 65,
      "lesson_attempts": 1,
      "completed_at": null,
      "words_mastered": 4,
      "words_total": 8
    }
  ],
  "recent_activity": [
    {
      "type": "lesson_completed",
      "lesson_title": "Greetings",
      "score": 85,
      "coins_earned": 85,
      "timestamp": "2024-01-15T14:45:00Z"
    },
    {
      "type": "word_practiced",
      "word": "hello",
      "correct": true,
      "timestamp": "2024-01-15T14:30:00Z"
    }
  ]
}
```

### Complete Lesson
`POST /api/v1/student/lessons/2/complete`

**Request:**
```json
{
  "score": 90,
  "word_results": [
    {
      "word_id": 3,
      "correct": true,
      "attempts": 1
    },
    {
      "word_id": 4,
      "correct": false,
      "attempts": 2
    },
    {
      "word_id": 5,
      "correct": true,
      "attempts": 1
    }
  ]
}
```

**Response:**
```json
{
  "message": "Lesson completed successfully",
  "results": {
    "score": 90,
    "previous_best": 65,
    "improvement": 25,
    "coins_earned": 25,
    "total_coins": 475,
    "new_rank": 2,
    "achievements": [
      "First time scoring 90+",
      "Climbed to rank 2"
    ]
  },
  "next_lesson": {
    "id": 3,
    "title": "Colors",
    "unlocked": true
  }
}
```

## Gamification & Competition

### Get Leaderboard
`GET /api/v1/student/leaderboard`

**Response:**
```json
[
  {
    "rank": 1,
    "student_name": "Alex Top",
    "total_coins": 850,
    "lessons_completed": 12,
    "avatar": "👑"
  },
  {
    "rank": 2,
    "student_name": "Current User",
    "total_coins": 475,
    "lessons_completed": 6,
    "avatar": "🌟",
    "is_me": true
  },
  {
    "rank": 3,
    "student_name": "Sam Learning",
    "total_coins": 420,
    "lessons_completed": 5,
    "avatar": "📚"
  }
]
```

### Achievements & Rewards

**Coin Earning System:**
- **First Attempt**: Full lesson score (0-100 coins)
- **Improvement**: Difference between attempts (e.g., 65→90 = +25 coins)
- **Perfect Score**: Bonus +10 coins for 100% score
- **Streak Bonus**: +5 coins per day for consecutive study days
- **Weekly Challenge**: Bonus coins for completing weekly goals

**Achievement Types:**
- **Progress Milestones**: Complete 1st, 5th, 10th lesson
- **Score Achievements**: First 80+, 90+, 100% scores
- **Streak Rewards**: Study for 3, 7, 14 consecutive days
- **Speed Learning**: Complete lesson in under X minutes
- **Perfectionist**: 100% score on first attempt

## Learning Features

### Adaptive Learning
- **Difficulty Adjustment**: System adapts based on performance
- **Personalized Review**: Focus on challenging words
- **Smart Spacing**: Review words at optimal intervals
- **Progress-Based Unlocking**: Unlock content based on mastery

### Interactive Elements
- **Audio Pronunciation**: Native speaker recordings
- **Visual Learning**: Images for vocabulary
- **Example Sentences**: Context-based learning
- **Multiple Attempts**: Learn from mistakes without penalty

### Study Modes
- **Practice Mode**: Review without affecting scores
- **Challenge Mode**: Timed exercises for bonus coins
- **Review Mode**: Revisit previously learned content
- **Mixed Practice**: Random words from multiple lessons

## Social Features

### Competition
- **Learning Center Leaderboard**: Compete with classmates
- **Weekly Challenges**: Group goals and achievements
- **Study Buddies**: See friends' progress (if enabled)
- **Class Rankings**: Position within assigned groups

### Motivation
- **Progress Visualization**: Charts and progress bars
- **Streak Tracking**: Consecutive study day counter
- **Goal Setting**: Weekly lesson completion targets
- **Celebration**: Animations and rewards for milestones

## Access Control

### Content Access
- **Progressive Unlocking**: Complete prerequisites to unlock new content
- **Group-Based Content**: Access to courses assigned by teachers
- **Payment Dependency**: Access blocked if learning center is unpaid

### Privacy
- **Secure Progress**: All data protected and encrypted
- **Limited Sharing**: Control over what classmates can see
- **Teacher Visibility**: Teachers can monitor academic progress only

## Error Responses

### 402 Payment Required
```json
{
  "detail": "Learning center subscription expired"
}
```

### 404 Not Found
```json
{
  "detail": "Lesson not found or not accessible"
}
```

### 423 Locked
```json
{
  "detail": "Complete previous lessons to unlock this content"
}
```

## Key Features

- **Gamified learning**: Coins, achievements, and leaderboards
- **Progressive difficulty**: Adaptive content based on performance
- **Rich media**: Audio and visual learning aids
- **Performance tracking**: Detailed analytics and progress reports
- **Social competition**: Leaderboards and group challenges
- **Personalized experience**: Tailored content and review schedules
- **Mobile-friendly**: Optimized for learning on any device
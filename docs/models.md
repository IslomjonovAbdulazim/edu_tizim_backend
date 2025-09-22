# Database Models

## User Management

### User
- `id`: Integer (Primary Key)
- `phone`: String (Unique per Learning Center)
- `name`: String
- `role`: Enum (admin, teacher, student)
- `learning_center_id`: Integer (Foreign Key → LearningCenter)
- `coins`: Integer (Default: 0, for students)
- `is_active`: Boolean
- `deleted_at`: DateTime (Nullable, for soft delete)
- `created_at`: DateTime
- **Indexes:** `(phone, learning_center_id)`, `learning_center_id`

### LearningCenter
- `id`: Integer (Primary Key)
- `name`: String
- `logo`: String (File path)
- `phone`: String
- `student_limit`: Integer
- `teacher_limit`: Integer
- `group_limit`: Integer
- `is_active`: Boolean
- `deleted_at`: DateTime (Nullable, for soft delete)
- `created_at`: DateTime

## Content Management

### Course
- `id`: Integer (Primary Key)
- `title`: String
- `learning_center_id`: Integer (Foreign Key → LearningCenter)
- `is_active`: Boolean
- `deleted_at`: DateTime (Nullable, for soft delete)
- `created_at`: DateTime
- **Indexes:** `learning_center_id`

### Lesson
- `id`: Integer (Primary Key)
- `title`: String
- `content`: Text
- `order`: Integer
- `course_id`: Integer (Foreign Key → Course)
- `deleted_at`: DateTime (Nullable, for soft delete)
- `created_at`: DateTime
- **Indexes:** `course_id`

### Word
- `id`: Integer (Primary Key)
- `word`: String
- `translation`: String
- `definition`: Text
- `sentence`: String (Example sentence with the word)
- `difficulty`: Enum (easy, medium, hard)
- `audio`: String (File path)
- `image`: String (File path)
- `lesson_id`: Integer (Foreign Key → Lesson)
- `order`: Integer
- `deleted_at`: DateTime (Nullable, for soft delete)
- `created_at`: DateTime
- **Indexes:** `lesson_id`, `(lesson_id, order)`

## Group Management

### Group
- `id`: Integer (Primary Key)
- `name`: String
- `learning_center_id`: Integer (Foreign Key → LearningCenter)
- `course_id`: Integer (Foreign Key → Course)
- `teacher_id`: Integer (Foreign Key → User)
- `deleted_at`: DateTime (Nullable, for soft delete)
- `created_at`: DateTime
- **Indexes:** `learning_center_id`, `teacher_id`, `course_id`

### GroupStudent
- `id`: Integer (Primary Key)
- `group_id`: Integer (Foreign Key → Group)
- `student_id`: Integer (Foreign Key → User)
- `joined_at`: DateTime
- **Indexes:** `group_id`, `student_id`, `(group_id, student_id)`

## Progress Tracking

### LessonProgress
- `id`: Integer (Primary Key)
- `student_id`: Integer (Foreign Key → User)
- `lesson_id`: Integer (Foreign Key → Lesson)
- `best_score`: Integer (Default: 0, max 100)
- `total_coins_earned`: Integer (Default: 0)
- `lesson_attempts`: Integer (Default: 0)
- `completed_at`: DateTime (Nullable)
- `updated_at`: DateTime
- **Indexes:** `(student_id, lesson_id)`, `student_id`, `lesson_id`

### WordHistory
- `id`: Integer (Primary Key)
- `student_id`: Integer (Foreign Key → User)
- `word_id`: Integer (Foreign Key → Word)
- `is_correct`: Boolean
- `attempted_at`: DateTime
- **Indexes:** `(student_id, word_id)`, `student_id`, `word_id`

### CoinTransaction
- `id`: Integer (Primary Key)
- `student_id`: Integer (Foreign Key → User)
- `lesson_id`: Integer (Foreign Key → Lesson)
- `amount`: Integer
- `transaction_type`: Enum (lesson_score, bonus, penalty)
- `description`: String
- `created_at`: DateTime
- **Indexes:** `student_id`, `lesson_id`, `created_at`

### Leaderboard
- `id`: Integer (Primary Key)
- `learning_center_id`: Integer (Foreign Key → LearningCenter)
- `student_id`: Integer (Foreign Key → User)
- `total_coins`: Integer
- `rank`: Integer
- `updated_at`: DateTime
- **Indexes:** `learning_center_id`, `(learning_center_id, rank)`, `student_id`
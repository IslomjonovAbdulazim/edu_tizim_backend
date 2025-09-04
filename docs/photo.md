# Photo & Media Storage Documentation

## Overview
The system handles multiple types of media files including user avatars, learning center logos, word images, and word audio files. All media is stored in a persistent storage system with proper file organization and caching.

## Persistent Storage Architecture

### Storage Path Configuration
- **Environment Variable**: `STORAGE_PATH` (defaults to `/tmp/persistent_storage`)
- **Production**: Should point to persistent volume or cloud storage mount
- **Development**: Uses local temporary directory with fallback

### Directory Structure
```
/storage/
├── logos/          # Learning center logos (PNG only, max 3MB)
├── word-images/    # Word illustration images (PNG, JPG)
└── word-audio/     # Word pronunciation audio (MP3, WAV)
```

### File Organization
- **Unique Naming**: All files use UUID4 naming to prevent conflicts
- **Extension Preservation**: Original file extensions are maintained
- **Path Format**: `/storage/{folder}/{uuid}.{extension}`

## Database Schema

### User Avatars
```sql
users.avatar VARCHAR(200) -- Stores full URL/path to avatar image
```

### Learning Center Logos
```sql
learning_centers.logo VARCHAR(300) -- Stores relative path to logo file
```

### Word Media
```sql
words.image_url VARCHAR(300)  -- Relative path to word image
words.audio_url VARCHAR(300)  -- Relative path to word audio
```

## File Upload Endpoints

### 1. Word Image Upload
**Endpoint**: `POST /admin/words/{word_id}/image`
- **File Types**: PNG, JPG, JPEG, GIF
- **Max Size**: Configurable via FastAPI
- **Storage**: `/storage/word-images/`
- **Returns**: Success message with updated word data

### 2. Word Audio Upload
**Endpoint**: `POST /admin/words/{word_id}/audio`
- **File Types**: MP3, WAV, OGG
- **Storage**: `/storage/word-audio/`
- **Returns**: Success message with updated word data

### 3. Learning Center Logo Upload
**Endpoint**: `POST /admin/centers/{center_id}/logo`
- **File Types**: PNG only
- **Max Size**: 3MB
- **Storage**: `/storage/logos/`
- **Returns**: Success message with updated center data

## Storage Implementation

### File Saving Process
```python
def save_uploaded_file(file: UploadFile, folder: str) -> str:
    # 1. Validate file selection
    # 2. Create storage directory if needed
    # 3. Generate UUID4 filename with original extension
    # 4. Write file to persistent storage
    # 5. Return relative path for database storage
```

### Storage Mounting
```python
# Mount static files for serving
app.mount("/storage", StaticFiles(directory=storage_path), name="storage")
```

## Caching Strategy

### Redis Caching
- **Content Cache**: Course structure cached for 1 hour
- **Word Cache**: Lesson words cached for 30 minutes
- **Leaderboard Cache**: User rankings cached for 5 minutes

### Cache Keys
- `content:center:{center_id}` - Complete course structure
- `words:lesson:{lesson_id}` - Lesson vocabulary with media URLs
- `leaderboard:center:{center_id}` - Center student rankings

### Cache Invalidation
```python
ContentService.invalidate_center_cache(center_id)
```
Clears all related caches when content is modified.

## File Access & Security

### Public Access
- All files in `/storage/` are publicly accessible via HTTP
- Files are served through FastAPI's StaticFiles middleware
- No authentication required for file access

### File Validation
- **File Type Checking**: Based on file extension
- **Size Limits**: Enforced at upload time
- **Filename Sanitization**: UUID naming prevents path traversal

## Production Deployment

### Persistent Storage Options
1. **Docker Volumes**: Mount persistent volume to container
2. **Cloud Storage**: S3, GCS, or Azure Blob with local mount
3. **Network Storage**: NFS or similar network-attached storage

### Environment Configuration
```bash
# Production storage path
STORAGE_PATH=/opt/app/persistent_storage

# Ensure directory permissions
mkdir -p $STORAGE_PATH/{logos,word-images,word-audio}
chmod 755 $STORAGE_PATH
```

### Backup Considerations
- Regular backup of entire `/storage/` directory
- Database contains relative paths, enabling easy storage migration
- Consider versioning for file updates/changes

## Media Serving Performance

### Static File Serving
- Files served directly by FastAPI StaticFiles
- No database queries for file access
- Efficient for high-frequency media requests

### CDN Integration
For production scale:
- Upload files to cloud storage (S3, GCS)
- Update database URLs to point to CDN
- Maintain local storage for development

## File Lifecycle

### Upload Flow
1. User uploads file via admin interface
2. File validated and saved with UUID name
3. Database updated with relative path
4. Cache invalidated for affected content
5. File immediately accessible via `/storage/` URL

### Update Flow
1. New file uploaded replaces old reference
2. Old file remains on disk (cleanup required)
3. Database updated with new path
4. Cache cleared

### Cleanup Requirements
- Periodic cleanup of orphaned files
- Track file references in database
- Remove unreferenced files from storage
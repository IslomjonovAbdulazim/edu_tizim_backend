import re
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import httpx
from telegram_bot.config import bot_settings

logger = logging.getLogger(__name__)


def format_phone_number(phone: str) -> str:
    """Format phone number to standard format"""
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone.strip())

    # Handle different formats
    if cleaned.startswith('+998'):
        return cleaned
    elif cleaned.startswith('998'):
        return '+' + cleaned
    elif len(cleaned) == 9 and cleaned.isdigit():
        # Assume Uzbek number without country code
        return '+998' + cleaned
    elif cleaned.startswith('+'):
        return cleaned
    else:
        # Try to add +998 for short numbers
        if len(cleaned) == 9:
            return '+998' + cleaned
        return cleaned


def is_valid_phone(phone: str) -> bool:
    """Validate phone number format"""
    patterns = [
        r'^\+998\d{9}$',  # +998901234567
        r'^\+\d{10,15}$',  # International format
    ]

    return any(re.match(pattern, phone) for pattern in patterns)


def is_valid_verification_code(code: str) -> bool:
    """Check if text is a valid verification code"""
    return bool(re.match(r'^\d{6}$', code.strip()))


def format_datetime(dt: datetime) -> str:
    """Format datetime for user display"""
    if not dt:
        return "Never"

    now = datetime.now()
    diff = now - dt

    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"


def format_user_role(role: str) -> str:
    """Format user role for display"""
    role_mapping = {
        'student': '👨‍🎓 Student',
        'teacher': '👩‍🏫 Teacher',
        'parent': '👨‍👩‍👧‍👦 Parent',
        'admin': '👨‍💼 Administrator',
        'super_admin': '🦸‍♂️ Super Admin',
        'content_manager': '📚 Content Manager',
        'reception': '🏢 Reception',
        'group_manager': '👥 Group Manager'
    }
    return role_mapping.get(role.lower(), f'👤 {role.title()}')


def format_progress_bar(percentage: float, length: int = 10) -> str:
    """Create a visual progress bar"""
    if percentage < 0:
        percentage = 0
    elif percentage > 100:
        percentage = 100

    filled = int(percentage / 100 * length)
    empty = length - filled

    bar = "█" * filled + "░" * empty
    return f"{bar} {percentage:.1f}%"


def format_points(points: int) -> str:
    """Format points with emoji"""
    if points >= 1000:
        return f"⭐ {points:,} pts"
    else:
        return f"⭐ {points} pts"


def format_rank(rank: int) -> str:
    """Format rank with appropriate emoji"""
    if rank == 1:
        return "🥇 #1"
    elif rank == 2:
        return "🥈 #2"
    elif rank == 3:
        return "🥉 #3"
    elif rank <= 10:
        return f"🏆 #{rank}"
    else:
        return f"#{rank}"


def extract_callback_data(callback_data: str) -> Dict[str, str]:
    """Extract data from callback query"""
    parts = callback_data.split('_')
    if len(parts) >= 2:
        return {
            'action': parts[0],
            'type': parts[1] if len(parts) > 1 else None,
            'id': parts[2] if len(parts) > 2 else None,
            'extra': '_'.join(parts[3:]) if len(parts) > 3 else None
        }
    return {'action': callback_data}


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)].rstrip() + suffix


def escape_markdown(text: str) -> str:
    """Escape special characters for Markdown"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def format_lesson_stats(stats: Dict[str, Any]) -> str:
    """Format lesson statistics for display"""
    completion_rate = stats.get('completion_rate', 0)
    average_accuracy = stats.get('average_accuracy', 0)
    total_attempts = stats.get('total_attempts', 0)

    return (
        f"📊 **Lesson Statistics**\n\n"
        f"📈 Completion Rate: {completion_rate:.1f}%\n"
        f"🎯 Average Accuracy: {average_accuracy:.1f}%\n"
        f"👥 Total Attempts: {total_attempts}\n"
        f"📈 Progress: {format_progress_bar(completion_rate)}"
    )


def format_user_stats(stats: Dict[str, Any]) -> str:
    """Format user statistics for display"""
    total_points = stats.get('total_points', 0)
    lessons_completed = stats.get('lessons_completed', 0)
    current_rank = stats.get('current_rank_global')
    badges_count = stats.get('badges_earned', 0)

    text = f"📊 **Your Statistics**\n\n"
    text += f"{format_points(total_points)}\n"
    text += f"📚 Lessons Completed: {lessons_completed}\n"
    text += f"🎖 Badges Earned: {badges_count}\n"

    if current_rank:
        text += f"🏆 Global Rank: {format_rank(current_rank)}\n"

    return text


def validate_user_input(input_text: str, input_type: str) -> tuple[bool, str]:
    """Validate user input based on type"""
    if input_type == "phone":
        phone = format_phone_number(input_text)
        if is_valid_phone(phone):
            return True, phone
        else:
            return False, "Invalid phone number format. Please use format: +998901234567"

    elif input_type == "verification_code":
        if is_valid_verification_code(input_text):
            return True, input_text.strip()
        else:
            return False, "Verification code must be 6 digits"

    elif input_type == "name":
        name = input_text.strip()
        if len(name) >= 2 and len(name) <= 50:
            return True, name
        else:
            return False, "Name must be between 2 and 50 characters"

    else:
        return True, input_text.strip()


def calculate_time_remaining(expires_at: str) -> str:
    """Calculate and format time remaining until expiration"""
    try:
        expire_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        now = datetime.now(expire_time.tzinfo)

        if now >= expire_time:
            return "Expired"

        diff = expire_time - now
        minutes = int(diff.total_seconds() // 60)
        seconds = int(diff.total_seconds() % 60)

        if minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    except:
        return "Unknown"


def format_error_message(error_code: str, context: Dict[str, Any] = None) -> str:
    """Format error message based on error code"""
    error_messages = {
        'INVALID_CODE': bot_settings.ERROR_INVALID_CODE,
        'CODE_EXPIRED': bot_settings.ERROR_CODE_EXPIRED,
        'MAX_ATTEMPTS': bot_settings.ERROR_MAX_ATTEMPTS,
        'RATE_LIMITED': bot_settings.ERROR_RATE_LIMITED,
        'USER_NOT_FOUND': bot_settings.ERROR_USER_NOT_FOUND,
        'GENERAL_ERROR': bot_settings.ERROR_GENERAL
    }

    base_message = error_messages.get(error_code, bot_settings.ERROR_GENERAL)

    # Add context if provided
    if context:
        if 'attempts_remaining' in context and context['attempts_remaining'] > 0:
            base_message += f"\n\n🔄 Attempts remaining: {context['attempts_remaining']}"
        elif 'retry_after' in context:
            base_message += f"\n\n⏱ Try again in {context['retry_after']} seconds"

    return base_message


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split list into chunks of specified size"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def format_leaderboard_entry(entry: Dict[str, Any], user_rank: int = None) -> str:
    """Format leaderboard entry for display"""
    rank = entry.get('rank', 0)
    name = entry.get('user_full_name', 'Unknown')
    points = entry.get('points', 0)
    position_change = entry.get('position_change', 0)

    # Rank emoji
    rank_display = format_rank(rank)

    # Position change indicator
    change_indicator = ""
    if position_change > 0:
        change_indicator = f" ⬆️+{position_change}"
    elif position_change < 0:
        change_indicator = f" ⬇️{position_change}"

    # Highlight current user
    highlight = "**" if rank == user_rank else ""

    return f"{highlight}{rank_display} {truncate_text(name, 20)} - {format_points(points)}{change_indicator}{highlight}"


async def make_api_request(
        method: str,
        url: str,
        data: Dict = None,
        params: Dict = None,
        timeout: int = 10
) -> tuple[bool, Dict[str, Any]]:
    """Make HTTP request to API"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                json=data,
                params=params
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return False, {"error": f"HTTP {response.status_code}"}

    except httpx.TimeoutException:
        logger.error(f"API request timeout: {url}")
        return False, {"error": "Request timeout"}
    except Exception as e:
        logger.error(f"API request error: {e}")
        return False, {"error": str(e)}


def log_user_action(telegram_id: int, action: str, details: Dict = None):
    """Log user action for analytics/debugging"""
    log_data = {
        'telegram_id': telegram_id,
        'action': action,
        'timestamp': datetime.now().isoformat(),
        'details': details or {}
    }

    # In production, you might want to send this to a logging service
    logger.info(f"User Action: {log_data}")


def get_user_language(telegram_user) -> str:
    """Get user's language from Telegram user object"""
    if hasattr(telegram_user, 'language_code'):
        lang_code = telegram_user.language_code
        # Map to supported languages
        if lang_code.startswith('uz'):
            return 'uz'
        elif lang_code.startswith('ru'):
            return 'ru'
        else:
            return 'en'  # Default to English
    return 'en'


def format_time_ago(dt: datetime) -> str:
    """Format datetime as 'time ago' string"""
    if not dt:
        return "Never"

    now = datetime.now()
    if dt.tzinfo:
        now = now.replace(tzinfo=dt.tzinfo)

    diff = now - dt

    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"
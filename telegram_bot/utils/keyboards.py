from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram_bot.config import bot_settings


def get_phone_request_keyboard():
    """Get keyboard for requesting phone number"""
    keyboard = [
        [KeyboardButton(bot_settings.BUTTON_SHARE_PHONE, request_contact=True)]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="👆 Press the button to share your phone number"
    )


def get_main_keyboard():
    """Get main menu keyboard for verified users"""
    keyboard = [
        ["📊 My Progress", "🎯 Take Quiz"],
        ["🏆 Leaderboard", "🎖 My Badges"],
        ["👤 Profile", "ℹ️ Help"]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        input_field_placeholder="Choose an option from the menu"
    )


def get_verification_keyboard(telegram_id: int, phone_number: str):
    """Get inline keyboard for verification actions"""
    keyboard = [
        [InlineKeyboardButton("🔄 Request New Code", callback_data=f"request_code_{telegram_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_verification")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_learning_keyboard():
    """Get keyboard for learning activities"""
    keyboard = [
        ["📚 Start Lesson", "📝 Take Quiz"],
        ["🔄 Practice Weak Words", "📊 View Progress"],
        ["🔙 Back to Main Menu"]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        input_field_placeholder="Select a learning activity"
    )


def get_progress_keyboard():
    """Get keyboard for progress-related actions"""
    keyboard = [
        ["📈 Overall Progress", "📊 Course Progress"],
        ["🎯 Lesson Stats", "📉 Weak Words"],
        ["🔙 Back to Main Menu"]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        input_field_placeholder="Choose what progress to view"
    )


def get_quiz_keyboard():
    """Get keyboard for quiz options"""
    keyboard = [
        ["🎯 Start New Quiz", "📊 Quiz History"],
        ["🔄 Practice Mode", "🎲 Random Quiz"],
        ["🔙 Back to Main Menu"]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        input_field_placeholder="Select quiz option"
    )


def get_profile_keyboard():
    """Get keyboard for profile management"""
    keyboard = [
        ["👤 View Profile", "✏️ Edit Profile"],
        ["📱 Change Phone", "🔐 Security"],
        ["🔙 Back to Main Menu"]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        input_field_placeholder="Choose profile option"
    )


def get_admin_keyboard():
    """Get keyboard for admin users"""
    keyboard = [
        ["👥 Manage Users", "📚 Manage Content"],
        ["📊 View Analytics", "⚙️ Settings"],
        ["🔙 Back to Main Menu"]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        input_field_placeholder="Admin panel - choose action"
    )


def get_teacher_keyboard():
    """Get keyboard for teacher users"""
    keyboard = [
        ["👨‍🎓 My Students", "📚 Course Content"],
        ["📊 Student Progress", "📝 Assignments"],
        ["🔙 Back to Main Menu"]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        input_field_placeholder="Teacher panel - choose action"
    )


def get_confirmation_keyboard(action: str, item_id: str = None):
    """Get inline confirmation keyboard"""
    callback_data_yes = f"confirm_{action}_{item_id}" if item_id else f"confirm_{action}"
    callback_data_no = f"cancel_{action}_{item_id}" if item_id else f"cancel_{action}"

    keyboard = [
        [
            InlineKeyboardButton("✅ Yes", callback_data=callback_data_yes),
            InlineKeyboardButton("❌ No", callback_data=callback_data_no)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_pagination_keyboard(current_page: int, total_pages: int, callback_prefix: str):
    """Get inline keyboard for pagination"""
    keyboard = []

    # Navigation row
    nav_buttons = []

    # Previous page button
    if current_page > 1:
        nav_buttons.append(
            InlineKeyboardButton("⬅️ Previous", callback_data=f"{callback_prefix}_page_{current_page - 1}")
        )

    # Page indicator
    nav_buttons.append(
        InlineKeyboardButton(f"📄 {current_page}/{total_pages}", callback_data="page_info")
    )

    # Next page button
    if current_page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton("Next ➡️", callback_data=f"{callback_prefix}_page_{current_page + 1}")
        )

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Quick jump buttons for first/last pages if not already visible
    jump_buttons = []
    if current_page > 2:
        jump_buttons.append(
            InlineKeyboardButton("⏮️ First", callback_data=f"{callback_prefix}_page_1")
        )
    if current_page < total_pages - 1:
        jump_buttons.append(
            InlineKeyboardButton("Last ⏭️", callback_data=f"{callback_prefix}_page_{total_pages}")
        )

    if jump_buttons:
        keyboard.append(jump_buttons)

    return InlineKeyboardMarkup(keyboard)


def get_language_selection_keyboard():
    """Get keyboard for language selection"""
    keyboard = [
        [
            InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
            InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")
        ],
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_course_selection_keyboard(courses: list):
    """Get inline keyboard for course selection"""
    keyboard = []

    # Add course buttons (2 per row)
    for i in range(0, len(courses), 2):
        row = []
        for j in range(2):
            if i + j < len(courses):
                course = courses[i + j]
                row.append(
                    InlineKeyboardButton(
                        f"📚 {course['name']}",
                        callback_data=f"course_{course['id']}"
                    )
                )
        keyboard.append(row)

    # Add back button
    keyboard.append([
        InlineKeyboardButton("🔙 Back", callback_data="back_to_main")
    ])

    return InlineKeyboardMarkup(keyboard)


def get_lesson_keyboard(lesson_id: int, has_previous: bool = False, has_next: bool = False):
    """Get inline keyboard for lesson actions"""
    keyboard = []

    # Main lesson actions
    keyboard.append([
        InlineKeyboardButton("▶️ Start Lesson", callback_data=f"start_lesson_{lesson_id}"),
        InlineKeyboardButton("📊 View Stats", callback_data=f"lesson_stats_{lesson_id}")
    ])

    # Navigation buttons
    nav_buttons = []
    if has_previous:
        nav_buttons.append(
            InlineKeyboardButton("⬅️ Previous", callback_data=f"prev_lesson_{lesson_id}")
        )
    if has_next:
        nav_buttons.append(
            InlineKeyboardButton("Next ➡️", callback_data=f"next_lesson_{lesson_id}")
        )

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Back to course button
    keyboard.append([
        InlineKeyboardButton("🔙 Back to Course", callback_data="back_to_course")
    ])

    return InlineKeyboardMarkup(keyboard)


def get_quiz_options_keyboard(lesson_id: int):
    """Get inline keyboard for quiz options"""
    keyboard = [
        [
            InlineKeyboardButton("🎯 Full Quiz", callback_data=f"quiz_full_{lesson_id}"),
            InlineKeyboardButton("⚡ Quick Quiz", callback_data=f"quiz_quick_{lesson_id}")
        ],
        [
            InlineKeyboardButton("🔄 Practice Mode", callback_data=f"quiz_practice_{lesson_id}"),
            InlineKeyboardButton("🎲 Random Words", callback_data=f"quiz_random_{lesson_id}")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_to_lesson")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def remove_keyboard():
    """Remove custom keyboard"""
    from telegram import ReplyKeyboardRemove
    return ReplyKeyboardRemove()


def get_contact_keyboard():
    """Get keyboard with contact button"""
    return get_phone_request_keyboard()  # Alias for consistency


def get_help_keyboard():
    """Get keyboard for help options"""
    keyboard = [
        ["📖 Getting Started", "❓ FAQ"],
        ["📞 Contact Support", "🔙 Back to Main Menu"]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        input_field_placeholder="Choose help topic"
    )
import os
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .database import SessionLocal, RedisService
from .models import User, TelegramOTP, UserRole
from .utils import format_phone, validate_phone, validate_uzbek_phone, generate_verification_code, format_phone_display

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
            return
        
        self.application = Application.builder().token(self.token).build()
        self._setup_handlers()
    
    def _setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(MessageHandler(filters.CONTACT, self.handle_contact))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
    
    def _get_reply_contact_keyboard(self):
        """Get reply keyboard for contact sharing"""
        keyboard = [[KeyboardButton("📱 Telefon raqamini ulashish", request_contact=True)]]
        return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_id = str(update.effective_user.id)
        db = SessionLocal()
        
        try:
            # Check if user exists with this telegram_id
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            
            if user and user.phone:
                # User exists with phone, generate/send code
                await self.generate_and_send_code(update, user.phone, telegram_id)
            else:
                # Request phone number
                await update.message.reply_text(
                    "👋 Xush kelibsiz! Tasdiqlash kodlarini olish uchun telefon raqamingizni ulashing.",
                    reply_markup=self._get_reply_contact_keyboard()
                )
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        finally:
            db.close()
    
    async def handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_id = str(update.effective_user.id)
        phone = update.message.contact.phone_number
        
        # Clean phone number format
        phone = format_phone(phone)
        
        # Validate phone number
        if not validate_uzbek_phone(phone):
            await update.message.reply_text("❌ Telefon raqami formati noto'g'ri. Qaytadan urinib ko'ring.")
            return
        
        db = SessionLocal()
        try:
            # Check if user exists with this phone
            user = db.query(User).filter(User.phone == phone).first()
            
            if user:
                # Update telegram_id for existing user
                user.telegram_id = telegram_id
                db.commit()
                
                # Auto-generate and send code
                await self.generate_and_send_code(update, phone, telegram_id)
            else:
                # Create new user record
                new_user = User(
                    phone=phone,
                    telegram_id=telegram_id,
                    role=UserRole.STUDENT,
                    is_active=True
                )
                db.add(new_user)
                db.commit()
                
                # Auto-generate and send code for new user
                await self.generate_and_send_code(update, phone, telegram_id)
        except Exception as e:
            logger.error(f"Error handling contact: {e}")
            await update.message.reply_text("❌ Telefon raqamini saqlashda xatolik. Qaytadan urinib ko'ring.")
        finally:
            db.close()
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        telegram_id = str(update.effective_user.id)
        
        # Handle manual phone number input
        if text.startswith('+') or text.isdigit():
            phone = format_phone(text)
            
            if validate_uzbek_phone(phone):
                db = SessionLocal()
                try:
                    user = db.query(User).filter(User.phone == phone).first()
                    
                    if user:
                        user.telegram_id = telegram_id
                        db.commit()
                        await self.generate_and_send_code(update, phone, telegram_id)
                    else:
                        new_user = User(
                            phone=phone,
                            telegram_id=telegram_id,
                            role=UserRole.STUDENT,
                            is_active=True
                        )
                        db.add(new_user)
                        db.commit()
                        await self.generate_and_send_code(update, phone, telegram_id)
                except Exception as e:
                    logger.error(f"Error handling phone text: {e}")
                    await update.message.reply_text("❌ Telefon raqamini saqlashda xatolik.")
                finally:
                    db.close()
            else:
                await update.message.reply_text("❌ Telefon raqami formati noto'g'ri. Qaytadan urinib ko'ring.")
        else:
            # Any other text - check if user has phone and auto-send code
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.telegram_id == telegram_id).first()
                
                if user and user.phone:
                    # User has phone, auto-generate code
                    await self.generate_and_send_code(update, user.phone, telegram_id)
                else:
                    # No phone number, ask for it
                    await update.message.reply_text(
                        "📱 Tasdiqlash kodlarini olish uchun avval telefon raqamingizni ulashing.",
                        reply_markup=self._get_reply_contact_keyboard()
                    )
            except Exception as e:
                logger.error(f"Error handling text: {e}")
                await update.message.reply_text("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.")
            finally:
                db.close()
    
    async def generate_and_send_code(self, update: Update, phone: str, telegram_id: str):
        """Generate verification code and send it, reusing if <1min remaining"""
        try:
            # Check Redis for existing code
            existing_code = RedisService.get_verification_code(phone)
            ttl = RedisService.get_verification_code_ttl(phone) if existing_code else 0
            
            # If code exists and has more than 60 seconds remaining, reuse it
            if existing_code and ttl > 60:
                formatted_phone = format_phone_display(phone)
                await update.message.reply_text(
                    f"📱 Telefon raqamingiz: *{formatted_phone}*\n"
                    f"🔐 Tasdiqlash kodingiz: *{existing_code}*\n"
                    f"⏱️ Amal qilish muddati: *{ttl} soniya*",
                    parse_mode='Markdown'
                )
                return
            
            # Generate new code
            new_code = generate_verification_code()
            
            # Store in Redis with 5 minutes expiration
            if RedisService.store_verification_code(phone, new_code, 300):
                formatted_phone = format_phone_display(phone)
                await update.message.reply_text(
                    f"📱 Telefon raqamingiz: *{formatted_phone}*\n"
                    f"🔐 Tasdiqlash kodingiz: *{new_code}*\n"
                    f"⏱️ Amal qilish muddati: *300 soniya*",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Tasdiqlash kodini yaratib bo'lmadi. Qaytadan urinib ko'ring.")
                
        except Exception as e:
            logger.error(f"Error generating/sending code: {e}")
            await update.message.reply_text("❌ Tasdiqlash kodini yaratishda xatolik.")
    
    async def send_otp_to_telegram(self, phone: str, otp_code: str):
        """Send OTP code to user's Telegram chat"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.phone == phone).first()
            
            if user and user.telegram_id:
                try:
                    # Store in database
                    expires_at = datetime.now() + timedelta(minutes=5)
                    otp_record = TelegramOTP(
                        phone=phone,
                        telegram_id=user.telegram_id,
                        otp_code=otp_code,
                        expires_at=expires_at
                    )
                    db.add(otp_record)
                    db.commit()
                    
                    # Send to Telegram
                    await self.application.bot.send_message(
                        chat_id=user.telegram_id,
                        text=f"🔐 Your verification code: `{otp_code}`\n⏱️ Expires in 5 minutes",
                        parse_mode='Markdown'
                    )
                    
                    # Mark as sent
                    otp_record.is_sent = True
                    db.commit()
                    
                    return True
                except Exception as e:
                    logger.error(f"Error sending Telegram message: {e}")
                    return False
            else:
                logger.warning(f"No Telegram ID found for phone {phone}")
                return False
        except Exception as e:
            logger.error(f"Error in send_otp_to_telegram: {e}")
            return False
        finally:
            db.close()
    
    async def start_polling(self):
        """Start the bot with polling"""
        if not self.token:
            logger.error("Cannot start bot: TELEGRAM_BOT_TOKEN not set")
            return
        
        logger.info("Starting Telegram bot...")
        # Use the simpler run_polling method that handles lifecycle automatically
        await self.application.run_polling(drop_pending_updates=True)
    
    async def start_webhook(self, webhook_url: str):
        """Start the bot with webhook"""
        if not self.token:
            logger.error("Cannot start bot: TELEGRAM_BOT_TOKEN not set")
            return
        
        await self.application.bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set to: {webhook_url}")

# Global bot instance
telegram_bot = TelegramBot()
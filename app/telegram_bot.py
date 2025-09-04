import os
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .database import SessionLocal, RedisService
from .models import User, TelegramOTP, UserRole

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
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_id = str(update.effective_user.id)
        db = SessionLocal()
        
        try:
            # Check if user exists with this telegram_id
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            
            if user and user.phone:
                # User exists with phone, check for OTP codes
                await self.send_stored_otp(update, user.phone, telegram_id)
            else:
                # Request phone number
                keyboard = [[KeyboardButton("📱 Share Phone Number", request_contact=True)]]
                reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
                
                await update.message.reply_text(
                    "👋 Welcome! Please share your phone number to receive OTP codes.",
                    reply_markup=reply_markup
                )
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
        finally:
            db.close()
    
    async def handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_id = str(update.effective_user.id)
        phone = update.message.contact.phone_number
        
        # Clean phone number format
        if phone.startswith('+'):
            phone = phone[1:]
        
        db = SessionLocal()
        try:
            # Check if user exists with this phone
            user = db.query(User).filter(User.phone == phone).first()
            
            if user:
                # Update telegram_id for existing user
                user.telegram_id = telegram_id
                db.commit()
                
                await update.message.reply_text(
                    f"✅ Phone number {phone} linked to your Telegram account!",
                    reply_markup=ReplyKeyboardRemove()
                )
                
                # Check for existing OTP codes
                await self.send_stored_otp(update, phone, telegram_id)
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
                
                await update.message.reply_text(
                    f"✅ New account created with phone {phone}!\nYou'll receive OTP codes here when requested.",
                    reply_markup=ReplyKeyboardRemove()
                )
        except Exception as e:
            logger.error(f"Error handling contact: {e}")
            await update.message.reply_text("❌ Error saving phone number. Please try again.")
        finally:
            db.close()
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        
        # Handle manual phone number input
        if text.startswith('+') or text.isdigit():
            telegram_id = str(update.effective_user.id)
            phone = text.replace('+', '').replace(' ', '').replace('-', '')
            
            if len(phone) >= 10:  # Basic validation
                db = SessionLocal()
                try:
                    user = db.query(User).filter(User.phone == phone).first()
                    
                    if user:
                        user.telegram_id = telegram_id
                        db.commit()
                        
                        await update.message.reply_text(f"✅ Phone number {phone} linked!")
                        await self.send_stored_otp(update, phone, telegram_id)
                    else:
                        new_user = User(
                            phone=phone,
                            telegram_id=telegram_id,
                            role=UserRole.STUDENT,
                            is_active=True
                        )
                        db.add(new_user)
                        db.commit()
                        
                        await update.message.reply_text(f"✅ New account created with phone {phone}!")
                except Exception as e:
                    logger.error(f"Error handling phone text: {e}")
                    await update.message.reply_text("❌ Error saving phone number.")
                finally:
                    db.close()
            else:
                await update.message.reply_text("❌ Invalid phone number format. Please try again.")
        else:
            await update.message.reply_text("Please use /start command or share your phone number.")
    
    async def send_stored_otp(self, update: Update, phone: str, telegram_id: str):
        db = SessionLocal()
        try:
            # Check for unexpired OTP codes
            current_time = datetime.now()
            otp_record = db.query(TelegramOTP).filter(
                and_(
                    TelegramOTP.phone == phone,
                    TelegramOTP.telegram_id == telegram_id,
                    TelegramOTP.expires_at > current_time
                )
            ).order_by(TelegramOTP.created_at.desc()).first()
            
            if otp_record:
                await update.message.reply_text(f"🔐 Your OTP code: `{otp_record.otp_code}`", parse_mode='Markdown')
                
                # Mark as sent
                otp_record.is_sent = True
                db.commit()
            else:
                # Also check Redis for verification codes
                redis_code = RedisService.get_verification_code(phone)
                if redis_code:
                    await update.message.reply_text(f"🔐 Your verification code: `{redis_code}`", parse_mode='Markdown')
                else:
                    await update.message.reply_text("ℹ️ No active OTP codes found for your number.")
        except Exception as e:
            logger.error(f"Error sending stored OTP: {e}")
            await update.message.reply_text("❌ Error retrieving OTP code.")
        finally:
            db.close()
    
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
    
    def start_polling(self):
        """Start the bot with polling"""
        if not self.token:
            logger.error("Cannot start bot: TELEGRAM_BOT_TOKEN not set")
            return
        
        logger.info("Starting Telegram bot...")
        self.application.run_polling()
    
    async def start_webhook(self, webhook_url: str):
        """Start the bot with webhook"""
        if not self.token:
            logger.error("Cannot start bot: TELEGRAM_BOT_TOKEN not set")
            return
        
        await self.application.bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set to: {webhook_url}")

# Global bot instance
telegram_bot = TelegramBot()
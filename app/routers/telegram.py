from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
import random
import string
import logging
from datetime import datetime, timedelta

from ..database import get_db, RedisService
from ..models import User, TelegramOTP
from ..telegram_bot import telegram_bot

logger = logging.getLogger(__name__)

router = APIRouter()

class SendOTPRequest(BaseModel):
    phone: str

class TelegramWebhookRequest(BaseModel):
    pass  # Telegram sends complex JSON, handle in raw request

@router.post("/send-otp")
async def send_otp_to_telegram(request: SendOTPRequest, db: Session = Depends(get_db)):
    """Send OTP code to user's Telegram chat"""
    try:
        # Generate OTP code
        otp_code = ''.join(random.choices(string.digits, k=6))
        
        # Store in Redis (existing system)
        RedisService.store_verification_code(request.phone, otp_code, expire=300)
        
        # Try to send via Telegram
        telegram_sent = await telegram_bot.send_otp_to_telegram(request.phone, otp_code)
        
        if telegram_sent:
            return {"message": "OTP sent to Telegram successfully", "method": "telegram"}
        else:
            return {"message": "OTP generated and stored", "method": "sms_fallback", "note": "User not found on Telegram"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending OTP: {str(e)}")

@router.get("/check-telegram-user/{phone}")
async def check_telegram_user(phone: str, db: Session = Depends(get_db)):
    """Check if phone number is linked to Telegram"""
    user = db.query(User).filter(User.phone == phone).first()
    
    return {
        "phone": phone,
        "has_telegram": bool(user and user.telegram_id),
        "telegram_id": user.telegram_id if user else None
    }

@router.post("/webhook")
async def telegram_webhook(request: Request):
    """Handle Telegram webhook updates"""
    try:
        if not telegram_bot.token:
            raise HTTPException(status_code=500, detail="Bot not configured")
        
        json_data = await request.json()
        update = Update.de_json(json_data, telegram_bot.application.bot)
        
        if update:
            await telegram_bot.application.process_update(update)
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")
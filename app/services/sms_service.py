import httpx
from typing import Optional
import logging

from ..config import settings
from ..database import get_redis


logger = logging.getLogger(__name__)


class SMSService:
    TOKEN_KEY = "eskiz_token"
    
    def __init__(self):
        self.redis = get_redis()
    
    async def send_verification_code(self, phone: str, code: str) -> bool:
        """Send verification code via SMS"""
        try:
            # Use approved template
            message = f"Zehnly AI ilovasida ro'yxatdan o'tish uchun tasdiqlash kodi: {code}"
            await self._send_sms(phone, message)
            return True
        except Exception as e:
            logger.error(f"Failed to send verification SMS to {phone}: {str(e)}")
            return False
    
    async def _send_sms(self, phone: str, message: str) -> None:
        """Send SMS using Eskiz API"""
        token = await self._get_eskiz_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.ESKIZ_URL}/message/sms/send",
                json={
                    "mobile_phone": phone,
                    "message": message,
                    "from": settings.ESKIZ_FROM,
                    "callback_url": settings.ESKIZ_WEBHOOK_URL if settings.ESKIZ_WEBHOOK_URL else None,
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code != 200:
                raise Exception(f"SMS API error: {response.status_code} - {response.text}")
    
    async def _get_eskiz_token(self) -> str:
        """Get or refresh Eskiz token"""
        # Check if token exists in Redis
        token = self.redis.get(self.TOKEN_KEY)
        if token:
            return token
        
        # Get new token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.ESKIZ_URL}/auth/login",
                json={
                    "email": settings.ESKIZ_EMAIL,
                    "password": settings.ESKIZ_PASSWORD,
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to authenticate with Eskiz: {response.status_code}")
            
            data = response.json()
            token = data.get("data", {}).get("token")
            
            if not token:
                raise Exception("No token received from Eskiz API")
            
            # Store token for 29 days
            self.redis.setex(self.TOKEN_KEY, 60 * 60 * 24 * 29, token)
            
            return token


# Singleton instance
sms_service = SMSService()
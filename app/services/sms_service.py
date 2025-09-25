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
            message = f"Zehnly AI ilovasida ro'yxatdan o'tish uchun tasdiqlash kod: {code}"
            await self._send_sms(phone, message)
            return True
        except Exception as e:
            logger.error(f"Failed to send verification SMS to {phone}: {str(e)}")
            return False
    
    async def _send_sms(self, phone: str, message: str) -> None:
        """Send SMS using Eskiz API"""
        token = await self._get_eskiz_token()
        logger.info(f"Using token for SMS: {token[:20]}...{token[-10:]} (length: {len(token)})")
        
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
        token = await self.redis.get(self.TOKEN_KEY)
        if token:
            logger.info(f"Found cached token: {token[:20]}...{token[-10:]} (length: {len(token)})")
            return token
        
        logger.info("No cached token found, getting fresh token from Eskiz API")
        
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
                logger.error(f"No token in Eskiz response: {data}")
                raise Exception("No token received from Eskiz API")
            
            logger.info(f"Got fresh token: {token[:20]}...{token[-10:]} (length: {len(token)})")
            
            # Store token for 29 days
            await self.redis.setex(self.TOKEN_KEY, 60 * 60 * 24 * 29, token)
            logger.info("Token cached successfully in Redis")
            
            return token


# Singleton instance
sms_service = SMSService()
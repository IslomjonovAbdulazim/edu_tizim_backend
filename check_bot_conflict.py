#!/usr/bin/env python3
"""
Check for Telegram bot conflicts
"""

import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import Conflict, TelegramError

load_dotenv()

async def check_bot_conflict():
    """Check if bot token is in use"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ No TELEGRAM_BOT_TOKEN found in .env")
        return
    
    print(f"🔍 Checking bot token: {token[:10]}...")
    
    try:
        bot = Bot(token=token)
        
        # Try to get bot info
        bot_info = await bot.get_me()
        print(f"✅ Bot found: @{bot_info.username} ({bot_info.first_name})")
        
        # Try to get updates (this will fail if another instance is running)
        print("🔍 Testing for conflicts...")
        updates = await bot.get_updates(limit=1, timeout=1)
        print("✅ No conflicts detected - bot is available")
        
    except Conflict as e:
        print("❌ CONFLICT DETECTED!")
        print(f"📝 Error: {e}")
        print("\n💡 Solutions:")
        print("1. Stop other bot instances (production server, other terminals)")
        print("2. Add DISABLE_TELEGRAM_BOT=true to .env")
        print("3. Create separate development bot token")
        
    except TelegramError as e:
        print(f"❌ Telegram error: {e}")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def main():
    """Main function"""
    try:
        asyncio.run(check_bot_conflict())
    except KeyboardInterrupt:
        print("\n🛑 Check cancelled")

if __name__ == "__main__":
    main()
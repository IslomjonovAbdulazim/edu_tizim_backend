#!/usr/bin/env python3
"""
Standalone script to run the Telegram bot
Usage: python start_telegram_bot.py
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def main():
    # Import here to avoid circular imports
    from app.telegram_bot import telegram_bot
    
    if not telegram_bot.token:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment variables")
        print("Please set TELEGRAM_BOT_TOKEN in your .env file")
        return
    
    print("🤖 Starting Telegram bot...")
    print(f"🔑 Using token: {telegram_bot.token[:10]}...")
    
    try:
        # Start the bot
        telegram_bot.start_polling()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

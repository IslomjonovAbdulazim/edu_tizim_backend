#!/usr/bin/env python3
"""
Standalone script to run the Telegram bot
Usage: python start_telegram_bot.py
"""

import asyncio
import os
import sys
import signal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def run_bot():
    """Async function to run the bot"""
    # Import here to avoid circular imports
    from app.telegram_bot import TelegramBot
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment variables")
        print("Please set TELEGRAM_BOT_TOKEN in your .env file")
        return
    
    print("🤖 Starting Telegram bot...")
    print(f"🔑 Using token: {token[:10]}...")
    
    # Create bot instance
    bot = TelegramBot()
    
    # Start the bot with proper lifecycle
    await bot.application.initialize()
    await bot.application.start()
    
    try:
        await bot.application.updater.start_polling(drop_pending_updates=True)
        print("✅ Bot is running...")
        
        # Keep running until interrupted
        stop_event = asyncio.Event()
        
        def signal_handler():
            print("\n🛑 Shutting down bot...")
            stop_event.set()
        
        # Set up signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)
        
        await stop_event.wait()
        
    finally:
        print("🧹 Stopping bot...")
        await bot.application.updater.stop()
        await bot.application.stop()
        await bot.application.shutdown()
        print("✅ Bot stopped cleanly")

def main():
    """Main function"""
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot error: {e}")

if __name__ == "__main__":
    main()

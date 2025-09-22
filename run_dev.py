#!/usr/bin/env python3
"""
Development server runner with Telegram bot conflict prevention
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv

def main():
    """Run development server"""
    
    # Load environment variables
    load_dotenv()
    
    # Disable Telegram bot to avoid conflicts
    os.environ["DISABLE_TELEGRAM_BOT"] = "true"
    
    print("🚀 Starting FastAPI development server...")
    print("⚠️  Telegram bot disabled to avoid conflicts")
    print("💡 To enable bot: remove DISABLE_TELEGRAM_BOT or set to 'false'")
    print("=" * 60)
    
    # Run uvicorn server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        reload_dirs=["app"],
        log_level="info"
    )

if __name__ == "__main__":
    main()
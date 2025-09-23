#!/usr/bin/env python3
"""
Development runner for the Learning Center API
"""
import uvicorn
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("🚀 Starting Learning Center API Development Server...")
    print("📚 API Documentation: http://localhost:8001/docs")
    print("🔧 Redis UI: http://localhost:8001/redisinsight (if available)")
    print("🏥 Health Check: http://localhost:8001/health")
    print("📱 Learning Centers: http://localhost:8001/api/v1/auth/learning-centers")
    print("=" * 60)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
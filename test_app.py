#!/usr/bin/env python3
"""
Simple test script to verify the application can start
"""
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.main import app
    from app.config import settings
    print("✅ Application imports successful!")
    print(f"✅ Project: {settings.PROJECT_NAME}")
    print(f"✅ Database URL configured: {bool(settings.DATABASE_URL)}")
    print(f"✅ Redis URL configured: {bool(settings.REDIS_URL)}")
    print("✅ All basic configuration checks passed!")
    
    # Test basic route
    from fastapi.testclient import TestClient
    client = TestClient(app)
    
    # Test health endpoint
    response = client.get("/health")
    if response.status_code == 200:
        print("✅ Health endpoint working!")
    else:
        print(f"❌ Health endpoint failed: {response.status_code}")
    
    # Test learning centers endpoint (should work without auth)
    response = client.get("/api/v1/auth/learning-centers")
    print(f"✅ Learning centers endpoint status: {response.status_code}")
    
    print("\n🎉 Application is ready to run!")
    print("Run: uvicorn app.main:app --reload --host 0.0.0.0 --port 8001")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
#!/usr/bin/env python3
"""
Reset database by dropping and recreating all tables
"""
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base
from app import models  # Import all models to register them

def reset_database():
    """Drop and recreate all database tables"""
    try:
        print("Dropping all existing tables...")
        # Use raw SQL to drop all tables with CASCADE
        from sqlalchemy import text
        with engine.begin() as conn:
            # Get all table names
            result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
            tables = [row[0] for row in result]
            
            # Drop each table with CASCADE
            for table in tables:
                print(f"  Dropping table: {table}")
                conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
        
        print("✅ All tables dropped successfully!")
        
        print("Creating fresh database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        
        # List all created tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✅ Created {len(tables)} tables:")
        for table in sorted(tables):
            print(f"  - {table}")
            
    except Exception as e:
        print(f"❌ Error resetting database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    reset_database()
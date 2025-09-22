#!/usr/bin/env python3
"""
Database initialization script
Creates all tables and sets up super admin user
"""

import sys
import os
from sqlalchemy.exc import IntegrityError

# Add the current directory to the path to import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal
from app.models import Base, User, UserRole, LearningCenter
from app.utils import hash_password
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_tables():
    """Create all database tables"""
    print("🔨 Creating database tables...")
    try:
        # Create all tables defined in models
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

def create_super_admin():
    """Create super admin user"""
    db = SessionLocal()
    try:
        # Get credentials from environment
        admin_email = os.getenv("SUPER_ADMIN_EMAIL", "admin@gmail.com")
        admin_password = os.getenv("SUPER_ADMIN_PASSWORD", "admin123")
        
        print(f"👤 Creating super admin user: {admin_email}")
        
        # Check if super admin already exists
        existing_admin = db.query(User).filter(
            User.email == admin_email,
            User.role == UserRole.SUPER_ADMIN
        ).first()
        
        if existing_admin:
            print(f"⚠️  Super admin already exists with email: {admin_email}")
            print(f"📧 Email: {existing_admin.email}")
            print(f"🆔 ID: {existing_admin.id}")
            print(f"🔑 Role: {existing_admin.role.value}")
            return True
        
        # Create super admin user
        hashed_password = hash_password(admin_password)
        super_admin = User(
            email=admin_email,
            password_hash=hashed_password,
            role=UserRole.SUPER_ADMIN,
            is_active=True
        )
        
        db.add(super_admin)
        db.commit()
        db.refresh(super_admin)
        
        print("✅ Super admin created successfully!")
        print(f"📧 Email: {admin_email}")
        print(f"🔑 Password: {admin_password}")
        print(f"🆔 User ID: {super_admin.id}")
        
        return True
        
    except IntegrityError as e:
        db.rollback()
        print(f"❌ Super admin creation failed - user might already exist: {e}")
        return False
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating super admin: {e}")
        return False
    finally:
        db.close()

def create_everest_learning_center():
    """Create the default Everest Learning Center"""
    db = SessionLocal()
    try:
        print("🏫 Creating Everest Learning Center...")
        
        # Check if Everest center already exists
        existing_center = db.query(LearningCenter).filter(
            LearningCenter.id == 4
        ).first()
        
        if existing_center:
            print(f"⚠️  Everest Learning Center already exists:")
            print(f"🆔 ID: {existing_center.id}")
            print(f"📝 Title: {existing_center.title}")
            return True
        
        # Get super admin to be the owner
        super_admin = db.query(User).filter(
            User.role == UserRole.SUPER_ADMIN
        ).first()
        
        if not super_admin:
            print("❌ Super admin not found. Please create super admin first.")
            return False
        
        # Create Everest Learning Center with ID 4
        everest_center = LearningCenter(
            id=4,
            title="Everest Learning Center",
            logo=None,
            days_remaining=365,  # 1 year
            student_limit=1000,
            is_active=True,
            owner_id=super_admin.id
        )
        
        db.add(everest_center)
        db.commit()
        db.refresh(everest_center)
        
        print("✅ Everest Learning Center created successfully!")
        print(f"🆔 Center ID: {everest_center.id}")
        print(f"📝 Title: {everest_center.title}")
        print(f"👤 Owner: Super Admin (ID: {super_admin.id})")
        print(f"👥 Student Limit: {everest_center.student_limit}")
        print(f"📅 Days Remaining: {everest_center.days_remaining}")
        
        return True
        
    except IntegrityError as e:
        db.rollback()
        print(f"❌ Everest Learning Center creation failed: {e}")
        return False
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating Everest Learning Center: {e}")
        return False
    finally:
        db.close()

def main():
    """Main initialization function"""
    print("🚀 Starting database initialization...")
    print("=" * 50)
    
    # Step 1: Create tables
    if not create_tables():
        print("❌ Database initialization failed at table creation")
        return False
    
    print()
    
    # Step 2: Create super admin
    if not create_super_admin():
        print("❌ Database initialization failed at super admin creation")
        return False
    
    print()
    
    # Step 3: Create Everest Learning Center
    if not create_everest_learning_center():
        print("❌ Database initialization failed at Everest center creation")
        return False
    
    print()
    print("=" * 50)
    print("🎉 Database initialization completed successfully!")
    print()
    print("📋 Summary:")
    print("  ✅ All database tables created")
    print("  ✅ Super admin user created")
    print("  ✅ Everest Learning Center created")
    print()
    print("🔑 Super Admin Credentials:")
    print(f"  📧 Email: {os.getenv('SUPER_ADMIN_EMAIL', 'admin@gmail.com')}")
    print(f"  🔑 Password: {os.getenv('SUPER_ADMIN_PASSWORD', 'admin123')}")
    print()
    print("🏫 Default Learning Center:")
    print("  📝 Name: Everest Learning Center")
    print("  🆔 ID: 4")
    print("  👥 Student Limit: 1000")
    print()
    print("🚀 You can now start the FastAPI server!")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
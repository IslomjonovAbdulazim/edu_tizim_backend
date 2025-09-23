from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException, status

from ..models import User, LearningCenter, UserRole, Group, GroupStudent
from ..models import LessonProgress, CoinTransaction, TransactionType


class UserService:
    
    def create_user(
        self,
        db: Session,
        phone: str,
        name: str,
        role: UserRole,
        learning_center_id: int
    ) -> User:
        """Create a new user"""
        # Check learning center exists and limits
        learning_center = db.query(LearningCenter).filter(
            LearningCenter.id == learning_center_id,
            LearningCenter.is_active == True
        ).first()
        
        if not learning_center:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning center not found"
            )
        
        # Check if phone already exists in this learning center
        existing_user = db.query(User).filter(
            User.phone == phone,
            User.learning_center_id == learning_center_id
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered in this learning center"
            )
        
        # Check limits based on role
        if role == UserRole.STUDENT:
            student_count = db.query(User).filter(
                User.learning_center_id == learning_center_id,
                User.role == UserRole.STUDENT,
                User.is_active == True
            ).count()
            
            if student_count >= learning_center.student_limit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Student limit reached for this learning center"
                )
        
        elif role == UserRole.TEACHER:
            teacher_count = db.query(User).filter(
                User.learning_center_id == learning_center_id,
                User.role == UserRole.TEACHER,
                User.is_active == True
            ).count()
            
            if teacher_count >= learning_center.teacher_limit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Teacher limit reached for this learning center"
                )
        
        # Create user
        user = User(
            phone=phone,
            name=name,
            role=role,
            learning_center_id=learning_center_id
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
    
    def get_users_by_learning_center(
        self,
        db: Session,
        learning_center_id: int,
        role: Optional[UserRole] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """Get users by learning center with optional role filter"""
        query = db.query(User).filter(
            User.learning_center_id == learning_center_id,
            User.is_active == True
        )
        
        if role:
            query = query.filter(User.role == role)
        
        return query.offset(skip).limit(limit).all()
    
    def add_student_to_group(
        self,
        db: Session,
        student_id: int,
        group_id: int,
        current_user: User
    ) -> GroupStudent:
        """Add student to group"""
        # Verify group exists and user has permission
        group = db.query(Group).filter(Group.id == group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found"
            )
        
        # Check permissions
        if current_user.role == UserRole.TEACHER and group.teacher_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to manage this group"
            )
        
        if current_user.learning_center_id != group.learning_center_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized for this learning center"
            )
        
        # Verify student exists and is in same learning center
        student = db.query(User).filter(
            User.id == student_id,
            User.role == UserRole.STUDENT,
            User.learning_center_id == group.learning_center_id,
            User.is_active == True
        ).first()
        
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        # Check if already in group
        existing = db.query(GroupStudent).filter(
            GroupStudent.group_id == group_id,
            GroupStudent.student_id == student_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student already in group"
            )
        
        # Add to group
        group_student = GroupStudent(
            group_id=group_id,
            student_id=student_id
        )
        
        db.add(group_student)
        db.commit()
        db.refresh(group_student)
        
        return group_student
    
    def award_coins(
        self,
        db: Session,
        student_id: int,
        lesson_id: int,
        score: int,
        transaction_type: TransactionType = TransactionType.LESSON_SCORE,
        description: Optional[str] = None
    ) -> CoinTransaction:
        """Award coins to student"""
        student = db.query(User).filter(
            User.id == student_id,
            User.role == UserRole.STUDENT,
            User.is_active == True
        ).first()
        
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        # Create transaction
        transaction = CoinTransaction(
            student_id=student_id,
            lesson_id=lesson_id,
            amount=score,
            transaction_type=transaction_type,
            description=description or f"Lesson score: {score} points"
        )
        
        # Update student coins
        student.coins += score
        
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        
        return transaction


# Singleton instance
user_service = UserService()
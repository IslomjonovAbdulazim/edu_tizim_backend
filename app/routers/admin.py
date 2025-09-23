from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from ..database import get_db
from ..dependencies import get_admin_user
from ..models import User, UserRole, Group, GroupStudent, Course
from ..services import user_service
from sqlalchemy.sql import func


router = APIRouter()


class CreateUserRequest(BaseModel):
    phone: str
    name: str
    role: UserRole


class UserResponse(BaseModel):
    id: int
    phone: str
    name: str
    role: UserRole
    coins: int
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True


class CreateGroupRequest(BaseModel):
    name: str
    course_id: int
    teacher_id: int


class GroupResponse(BaseModel):
    id: int
    name: str
    course_id: int
    teacher_id: int
    student_count: int
    created_at: str
    
    class Config:
        from_attributes = True


class AddStudentToGroupRequest(BaseModel):
    student_id: int


class UpdateUserRequest(BaseModel):
    phone: Optional[str] = None
    name: Optional[str] = None
    role: Optional[UserRole] = None


class UpdateGroupRequest(BaseModel):
    name: Optional[str] = None
    course_id: Optional[int] = None
    teacher_id: Optional[int] = None


@router.post("/users", response_model=UserResponse)
async def create_user(
    request: CreateUserRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new user (student/teacher only)"""
    # Admin cannot create other admin accounts
    if request.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin accounts can only be created by Super Admin"
        )
    
    user = user_service.create_user(
        db=db,
        phone=request.phone,
        name=request.name,
        role=request.role,
        learning_center_id=current_user.learning_center_id
    )
    
    return user


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    role: UserRole = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List users in learning center"""
    users = user_service.get_users_by_learning_center(
        db=db,
        learning_center_id=current_user.learning_center_id,
        role=role,
        skip=skip,
        limit=limit
    )
    
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get specific user details"""
    user = db.query(User).filter(
        User.id == user_id,
        User.learning_center_id == current_user.learning_center_id,
        User.deleted_at.is_(None)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update user details"""
    user = db.query(User).filter(
        User.id == user_id,
        User.learning_center_id == current_user.learning_center_id,
        User.deleted_at.is_(None)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if phone number is unique within learning center (if updating phone)
    if request.phone and request.phone != user.phone:
        existing_phone = db.query(User).filter(
            User.phone == request.phone,
            User.learning_center_id == current_user.learning_center_id,
            User.id != user_id,
            User.deleted_at.is_(None)
        ).first()
        
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already exists in this learning center"
            )
    
    # Admin cannot change user role to admin
    if request.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role can only be assigned by Super Admin"
        )
    
    # Update fields if provided
    if request.phone:
        user.phone = request.phone
    if request.name:
        user.name = request.name
    if request.role:
        user.role = request.role
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Deactivate a user (soft delete)"""
    user = db.query(User).filter(
        User.id == user_id,
        User.learning_center_id == current_user.learning_center_id,
        User.deleted_at.is_(None)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Soft delete: mark as inactive and set deleted_at timestamp
    user.is_active = False
    user.deleted_at = func.now()
    db.commit()
    
    return {"message": "User deactivated successfully"}


# Group Management

@router.post("/groups", response_model=GroupResponse)
async def create_group(
    request: CreateGroupRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new group"""
    # Verify teacher exists and belongs to same learning center (exclude deleted)
    teacher = db.query(User).filter(
        User.id == request.teacher_id,
        User.role == UserRole.TEACHER,
        User.learning_center_id == current_user.learning_center_id,
        User.is_active == True,
        User.deleted_at.is_(None)
    ).first()
    
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher not found"
        )
    
    # Verify course exists and belongs to same learning center (exclude deleted)
    course = db.query(Course).filter(
        Course.id == request.course_id,
        Course.learning_center_id == current_user.learning_center_id,
        Course.is_active == True,
        Course.deleted_at.is_(None)
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    group = Group(
        name=request.name,
        learning_center_id=current_user.learning_center_id,
        course_id=request.course_id,
        teacher_id=request.teacher_id
    )
    
    db.add(group)
    db.commit()
    db.refresh(group)
    
    # Add student count
    group.student_count = 0
    
    return group


@router.get("/groups", response_model=List[GroupResponse])
async def list_groups(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List all groups in learning center"""
    groups = db.query(Group).filter(
        Group.learning_center_id == current_user.learning_center_id,
        Group.deleted_at.is_(None)
    ).offset(skip).limit(limit).all()
    
    # Add student counts
    for group in groups:
        student_count = db.query(GroupStudent).filter(
            GroupStudent.group_id == group.id
        ).count()
        group.student_count = student_count
    
    return groups


@router.get("/groups/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get specific group details"""
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.learning_center_id == current_user.learning_center_id,
        Group.deleted_at.is_(None)
    ).first()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Add student count
    student_count = db.query(GroupStudent).filter(
        GroupStudent.group_id == group.id
    ).count()
    group.student_count = student_count
    
    return group


@router.put("/groups/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: int,
    request: UpdateGroupRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update group details"""
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.learning_center_id == current_user.learning_center_id,
        Group.deleted_at.is_(None)
    ).first()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Validate teacher if updating (exclude deleted)
    if request.teacher_id:
        teacher = db.query(User).filter(
            User.id == request.teacher_id,
            User.role == UserRole.TEACHER,
            User.learning_center_id == current_user.learning_center_id,
            User.is_active == True,
            User.deleted_at.is_(None)
        ).first()
        
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Teacher not found"
            )
    
    # Validate course if updating (exclude deleted)
    if request.course_id:
        course = db.query(Course).filter(
            Course.id == request.course_id,
            Course.learning_center_id == current_user.learning_center_id,
            Course.is_active == True,
            Course.deleted_at.is_(None)
        ).first()
        
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
    
    # Update fields if provided
    if request.name:
        group.name = request.name
    if request.teacher_id:
        group.teacher_id = request.teacher_id
    if request.course_id:
        group.course_id = request.course_id
    
    db.commit()
    db.refresh(group)
    
    # Add student count
    student_count = db.query(GroupStudent).filter(
        GroupStudent.group_id == group.id
    ).count()
    group.student_count = student_count
    
    return group


@router.post("/groups/{group_id}/students")
async def add_student_to_group(
    group_id: int,
    request: AddStudentToGroupRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Add student to group"""
    group_student = user_service.add_student_to_group(
        db=db,
        student_id=request.student_id,
        group_id=group_id,
        current_user=current_user
    )
    
    return {"message": "Student added to group successfully"}


@router.delete("/groups/{group_id}/students/{student_id}")
async def remove_student_from_group(
    group_id: int,
    student_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Remove student from group"""
    # Verify group belongs to same learning center (exclude deleted)
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.learning_center_id == current_user.learning_center_id,
        Group.deleted_at.is_(None)
    ).first()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Remove student from group
    group_student = db.query(GroupStudent).filter(
        GroupStudent.group_id == group_id,
        GroupStudent.student_id == student_id
    ).first()
    
    if not group_student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not in group"
        )
    
    db.delete(group_student)
    db.commit()
    
    return {"message": "Student removed from group successfully"}


@router.delete("/groups/{group_id}")
async def delete_group(
    group_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Delete group (soft delete)"""
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.learning_center_id == current_user.learning_center_id,
        Group.deleted_at.is_(None)
    ).first()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    group.deleted_at = func.now()
    db.commit()
    
    return {"message": "Group deleted successfully"}
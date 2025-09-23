import os
import uuid
import shutil
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException

from ..config import settings


class StorageService:
    def __init__(self):
        self.storage_path = Path(settings.STORAGE_PATH)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories"""
        directories = [
            "logos",
            "audio",
            "images",
            "documents"
        ]
        
        for directory in directories:
            path = self.storage_path / directory
            path.mkdir(parents=True, exist_ok=True)
    
    async def save_logo(self, file: UploadFile, learning_center_id: int) -> str:
        """Save learning center logo"""
        return await self._save_file(file, "logos", f"center_{learning_center_id}")
    
    async def save_audio(self, file: UploadFile, word_id: int) -> str:
        """Save word audio file"""
        return await self._save_file(file, "audio", f"word_{word_id}")
    
    async def save_image(self, file: UploadFile, word_id: int) -> str:
        """Save word image file"""
        return await self._save_file(file, "images", f"word_{word_id}")
    
    async def _save_file(
        self, 
        file: UploadFile, 
        subdirectory: str, 
        prefix: str
    ) -> str:
        """Save file and return relative path"""
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix.lower()
        filename = f"{prefix}_{uuid.uuid4()}{file_extension}"
        
        # Create full path
        directory_path = self.storage_path / subdirectory
        file_path = directory_path / filename
        
        try:
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Return relative path for database storage
            return f"{subdirectory}/{filename}"
            
        except Exception as e:
            # Clean up if save failed
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to save file: {str(e)}"
            )
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file by relative path"""
        try:
            full_path = self.storage_path / file_path
            if full_path.exists():
                full_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def get_file_path(self, relative_path: str) -> Path:
        """Get full file path from relative path"""
        return self.storage_path / relative_path
    
    def file_exists(self, relative_path: str) -> bool:
        """Check if file exists"""
        return (self.storage_path / relative_path).exists()


# Singleton instance
storage_service = StorageService()
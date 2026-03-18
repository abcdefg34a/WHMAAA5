# ============================================================================
# SUPABASE STORAGE SERVICE
# ============================================================================

import os
from supabase import create_client, Client
import logging
from typing import Optional
import uuid
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')

class StorageService:
    """Service for Supabase Storage operations"""
    
    def __init__(self):
        if SUPABASE_URL and SUPABASE_SERVICE_KEY:
            self.client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
            self.enabled = True
            logger.info("✅ Supabase Storage Service initialized")
        else:
            self.client = None
            self.enabled = False
            logger.warning("⚠️ Supabase Storage not configured")
    
    async def upload_file(
        self, 
        bucket: str, 
        file_data: bytes, 
        file_name: str,
        content_type: str = "application/octet-stream"
    ) -> Optional[str]:
        """
        Upload a file to Supabase Storage
        Returns the storage path if successful
        """
        if not self.enabled:
            logger.warning("Storage not enabled, cannot upload file")
            return None
        
        try:
            # Generate unique path
            timestamp = datetime.utcnow().strftime("%Y/%m/%d")
            unique_id = str(uuid.uuid4())[:8]
            storage_path = f"{timestamp}/{unique_id}_{file_name}"
            
            # Upload file
            result = self.client.storage.from_(bucket).upload(
                path=storage_path,
                file=file_data,
                file_options={"content-type": content_type}
            )
            
            logger.info(f"✅ File uploaded to {bucket}/{storage_path}")
            return storage_path
            
        except Exception as e:
            logger.error(f"❌ Failed to upload file: {e}")
            return None
    
    async def get_signed_url(
        self, 
        bucket: str, 
        path: str, 
        expires_in: int = 3600
    ) -> Optional[str]:
        """
        Get a signed URL for private file access
        expires_in: seconds until URL expires (default 1 hour)
        """
        if not self.enabled:
            return None
        
        try:
            result = self.client.storage.from_(bucket).create_signed_url(
                path=path,
                expires_in=expires_in
            )
            return result.get('signedURL')
        except Exception as e:
            logger.error(f"❌ Failed to get signed URL: {e}")
            return None
    
    async def delete_file(self, bucket: str, path: str) -> bool:
        """Delete a file from storage"""
        if not self.enabled:
            return False
        
        try:
            self.client.storage.from_(bucket).remove([path])
            logger.info(f"✅ File deleted: {bucket}/{path}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete file: {e}")
            return False
    
    async def list_files(self, bucket: str, path: str = "") -> list:
        """List files in a bucket/path"""
        if not self.enabled:
            return []
        
        try:
            result = self.client.storage.from_(bucket).list(path)
            return result
        except Exception as e:
            logger.error(f"❌ Failed to list files: {e}")
            return []

# Global storage service instance
storage_service = StorageService()

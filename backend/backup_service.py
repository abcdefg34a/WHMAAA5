# ============================================================================
# BACKUP SERVICE FÜR MONGODB
# ============================================================================
# Vollständiges Backup- und Wiederherstellungssystem für:
# - MongoDB Datenbank
# - Dateien (Fotos, PDFs)
# - Automatische Kopie zu Supabase Storage (Cloud-Sicherung)
# ============================================================================

import os
import gzip
import shutil
import asyncio
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from io import BytesIO
import zipfile
import json
import logging
from bson import json_util
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# Backup Configuration
BACKUP_DIR = Path(__file__).parent / "backups"
BACKUP_DIR.mkdir(exist_ok=True)
BACKUP_TEMP_DIR = BACKUP_DIR / "temp"
BACKUP_TEMP_DIR.mkdir(exist_ok=True)

# Retention Settings
BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', 30))
BACKUP_RETENTION_MONTHS = int(os.environ.get('BACKUP_RETENTION_MONTHS', 12))

# Supabase Storage Configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
SUPABASE_BACKUP_BUCKET = "backups"  # Name des Backup-Buckets


class SupabaseStorageClient:
    """Client für Supabase Storage Operations"""
    
    def __init__(self):
        self.enabled = bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)
        self.client = None
        
        if self.enabled:
            try:
                from supabase import create_client, Client
                self.client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
                logger.info("✅ Supabase Storage Client initialisiert")
            except Exception as e:
                logger.error(f"❌ Supabase Storage Client Fehler: {e}")
                self.enabled = False
    
    async def ensure_bucket_exists(self) -> bool:
        """Stellt sicher, dass der Backup-Bucket existiert"""
        if not self.enabled or not self.client:
            return False
        
        try:
            # Versuche Bucket-Info abzurufen
            buckets = self.client.storage.list_buckets()
            bucket_names = [b.name for b in buckets]
            
            if SUPABASE_BACKUP_BUCKET not in bucket_names:
                # Bucket erstellen (privat)
                self.client.storage.create_bucket(
                    SUPABASE_BACKUP_BUCKET,
                    options={"public": False}
                )
                logger.info(f"✅ Supabase Bucket '{SUPABASE_BACKUP_BUCKET}' erstellt")
            else:
                logger.info(f"✅ Supabase Bucket '{SUPABASE_BACKUP_BUCKET}' existiert bereits")
            
            return True
        except Exception as e:
            logger.error(f"❌ Bucket-Prüfung fehlgeschlagen: {e}")
            return False
    
    async def upload_backup(self, local_path: Path, remote_path: str) -> Dict[str, Any]:
        """Lädt eine Backup-Datei zu Supabase Storage hoch"""
        if not self.enabled or not self.client:
            return {"success": False, "error": "Supabase nicht konfiguriert"}
        
        try:
            # Sicherstellen, dass Bucket existiert
            await self.ensure_bucket_exists()
            
            # Datei lesen
            with open(local_path, 'rb') as f:
                file_data = f.read()
            
            # Content-Type bestimmen
            if local_path.suffix == '.gz':
                content_type = 'application/gzip'
            elif local_path.suffix == '.zip':
                content_type = 'application/zip'
            else:
                content_type = 'application/octet-stream'
            
            # Upload zu Supabase
            result = self.client.storage.from_(SUPABASE_BACKUP_BUCKET).upload(
                path=remote_path,
                file=file_data,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            
            file_size = local_path.stat().st_size
            logger.info(f"✅ Backup zu Supabase hochgeladen: {remote_path} ({file_size} bytes)")
            
            return {
                "success": True,
                "remote_path": remote_path,
                "bucket": SUPABASE_BACKUP_BUCKET,
                "size_bytes": file_size
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Supabase Upload fehlgeschlagen: {error_msg}")
            return {"success": False, "error": error_msg}
    
    async def download_backup(self, remote_path: str) -> Optional[bytes]:
        """Lädt eine Backup-Datei von Supabase Storage herunter"""
        if not self.enabled or not self.client:
            return None
        
        try:
            response = self.client.storage.from_(SUPABASE_BACKUP_BUCKET).download(remote_path)
            logger.info(f"✅ Backup von Supabase heruntergeladen: {remote_path}")
            return response
        except Exception as e:
            logger.error(f"❌ Supabase Download fehlgeschlagen: {e}")
            return None
    
    async def delete_backup(self, remote_path: str) -> bool:
        """Löscht eine Backup-Datei aus Supabase Storage"""
        if not self.enabled or not self.client:
            return False
        
        try:
            self.client.storage.from_(SUPABASE_BACKUP_BUCKET).remove([remote_path])
            logger.info(f"✅ Backup aus Supabase gelöscht: {remote_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Supabase Löschung fehlgeschlagen: {e}")
            return False
    
    async def list_backups(self) -> List[Dict[str, Any]]:
        """Listet alle Backups in Supabase Storage"""
        if not self.enabled or not self.client:
            return []
        
        try:
            # Liste alle Dateien im Bucket
            files = []
            for folder in ['database/daily', 'database/monthly', 'storage/daily', 'storage/monthly']:
                try:
                    folder_files = self.client.storage.from_(SUPABASE_BACKUP_BUCKET).list(folder)
                    for f in folder_files:
                        if f.get('name') and not f.get('name').endswith('/'):
                            files.append({
                                "name": f.get('name'),
                                "path": f"{folder}/{f.get('name')}",
                                "size": f.get('metadata', {}).get('size', 0),
                                "created_at": f.get('created_at')
                            })
                except:
                    pass
            return files
        except Exception as e:
            logger.error(f"❌ Supabase Auflistung fehlgeschlagen: {e}")
            return []


class BackupService:
    """Service für MongoDB Backup und Wiederherstellung"""
    
    def __init__(self, db: AsyncIOMotorDatabase, mongo_url: str, db_name: str):
        self.db = db
        self.mongo_url = mongo_url
        self.db_name = db_name
        self.backup_dir = BACKUP_DIR
        
        # Initialize Supabase Storage Client
        self.supabase_storage = SupabaseStorageClient()
        
        # Create subdirectories
        (self.backup_dir / "database" / "daily").mkdir(parents=True, exist_ok=True)
        (self.backup_dir / "database" / "monthly").mkdir(parents=True, exist_ok=True)
        (self.backup_dir / "storage" / "daily").mkdir(parents=True, exist_ok=True)
        (self.backup_dir / "storage" / "monthly").mkdir(parents=True, exist_ok=True)
    
    # ========================================================================
    # DATABASE BACKUP
    # ========================================================================
    
    async def create_database_backup(
        self, 
        triggered_by_user_id: Optional[str] = None,
        retention_class: str = "daily"
    ) -> Dict[str, Any]:
        """
        Erstellt ein vollständiges MongoDB-Backup
        
        Args:
            triggered_by_user_id: ID des Admins (None für Cron-Jobs)
            retention_class: "daily" oder "monthly"
        
        Returns:
            Dict mit Backup-Informationen
        """
        backup_id = str(datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"))
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H-%M")
        filename = f"db-backup-{timestamp}.json.gz"
        
        backup_path = self.backup_dir / "database" / retention_class / filename
        
        # Create backup job record
        backup_job = {
            "id": backup_id,
            "backup_type": "database",
            "file_name": filename,
            "storage_path": str(backup_path.relative_to(self.backup_dir)),
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "file_size_bytes": 0,
            "triggered_by_user_id": triggered_by_user_id,
            "retention_class": retention_class,
            "error_message": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Save backup job to DB
        await self.db.backup_jobs.insert_one(backup_job)
        
        try:
            logger.info(f"Starting database backup: {filename}")
            
            # Export all collections
            backup_data = {}
            collections = await self.db.list_collection_names()
            
            for collection_name in collections:
                if collection_name.startswith("system."):
                    continue
                
                collection = self.db[collection_name]
                documents = await collection.find({}).to_list(length=None)
                
                # Convert ObjectId and dates to strings
                backup_data[collection_name] = json.loads(
                    json_util.dumps(documents)
                )
                
                logger.info(f"  Exported {len(documents)} documents from {collection_name}")
            
            # Add metadata
            backup_data["_backup_metadata"] = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "db_name": self.db_name,
                "collections": list(backup_data.keys()),
                "total_documents": sum(len(docs) for docs in backup_data.values() if isinstance(docs, list)),
                "version": "1.0"
            }
            
            # Write compressed backup
            json_str = json.dumps(backup_data, ensure_ascii=False, indent=2)
            
            with gzip.open(backup_path, 'wt', encoding='utf-8') as f:
                f.write(json_str)
            
            file_size = backup_path.stat().st_size
            
            # Update backup job
            await self.db.backup_jobs.update_one(
                {"id": backup_id},
                {"$set": {
                    "status": "success",
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "file_size_bytes": file_size
                }}
            )
            
            logger.info(f"Database backup completed: {filename} ({file_size} bytes)")
            
            # Upload to Supabase Storage (Cloud-Sicherung)
            supabase_result = None
            if self.supabase_storage.enabled:
                remote_path = f"database/{retention_class}/{filename}"
                supabase_result = await self.supabase_storage.upload_backup(backup_path, remote_path)
                
                # Update backup job with Supabase info
                if supabase_result.get("success"):
                    await self.db.backup_jobs.update_one(
                        {"id": backup_id},
                        {"$set": {
                            "supabase_path": remote_path,
                            "supabase_uploaded": True
                        }}
                    )
            
            # Log audit event
            await self._log_audit(
                "BACKUP_SUCCESS",
                triggered_by_user_id,
                "backup",
                backup_id,
                {
                    "type": "database",
                    "filename": filename,
                    "size_bytes": file_size,
                    "retention_class": retention_class,
                    "supabase_uploaded": supabase_result.get("success") if supabase_result else False
                }
            )
            
            return {
                "id": backup_id,
                "status": "success",
                "filename": filename,
                "path": str(backup_path),
                "size_bytes": file_size,
                "retention_class": retention_class,
                "supabase_uploaded": supabase_result.get("success") if supabase_result else False,
                "supabase_path": supabase_result.get("remote_path") if supabase_result and supabase_result.get("success") else None
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Database backup failed: {error_msg}")
            
            # Update backup job with error
            await self.db.backup_jobs.update_one(
                {"id": backup_id},
                {"$set": {
                    "status": "failed",
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "error_message": error_msg
                }}
            )
            
            # Log audit event
            await self._log_audit(
                "BACKUP_FAILED",
                triggered_by_user_id,
                "backup",
                backup_id,
                {"type": "database", "error": error_msg}
            )
            
            return {
                "id": backup_id,
                "status": "failed",
                "error": error_msg
            }
    
    # ========================================================================
    # STORAGE BACKUP
    # ========================================================================
    
    async def create_storage_backup(
        self,
        triggered_by_user_id: Optional[str] = None,
        retention_class: str = "daily"
    ) -> Dict[str, Any]:
        """
        Erstellt ein Backup aller Dateien (Fotos, PDFs)
        """
        backup_id = str(datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"))
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H-%M")
        filename = f"storage-backup-{timestamp}.zip"
        
        backup_path = self.backup_dir / "storage" / retention_class / filename
        
        # Create backup job record
        backup_job = {
            "id": backup_id,
            "backup_type": "storage",
            "file_name": filename,
            "storage_path": str(backup_path.relative_to(self.backup_dir)),
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "file_size_bytes": 0,
            "triggered_by_user_id": triggered_by_user_id,
            "retention_class": retention_class,
            "error_message": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.backup_jobs.insert_one(backup_job)
        
        try:
            logger.info(f"Starting storage backup: {filename}")
            
            # Get upload directory
            upload_dir = Path(__file__).parent / "uploads"
            
            files_backed_up = 0
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if upload_dir.exists():
                    for file_path in upload_dir.rglob("*"):
                        if file_path.is_file():
                            arcname = file_path.relative_to(upload_dir)
                            zipf.write(file_path, arcname)
                            files_backed_up += 1
                
                # Also backup base64 images stored in jobs
                jobs_with_photos = await self.db.jobs.find(
                    {"$or": [
                        {"photos": {"$exists": True, "$ne": []}},
                        {"service_photos": {"$exists": True, "$ne": []}}
                    ]},
                    {"_id": 0, "id": 1, "photos": 1, "service_photos": 1}
                ).to_list(length=None)
                
                photos_json = json.dumps(jobs_with_photos, default=str)
                zipf.writestr("job_photos_metadata.json", photos_json)
            
            file_size = backup_path.stat().st_size
            
            # Update backup job
            await self.db.backup_jobs.update_one(
                {"id": backup_id},
                {"$set": {
                    "status": "success",
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "file_size_bytes": file_size
                }}
            )
            
            logger.info(f"Storage backup completed: {filename} ({files_backed_up} files, {file_size} bytes)")
            
            # Upload to Supabase Storage (Cloud-Sicherung)
            supabase_result = None
            if self.supabase_storage.enabled:
                remote_path = f"storage/{retention_class}/{filename}"
                supabase_result = await self.supabase_storage.upload_backup(backup_path, remote_path)
                
                # Update backup job with Supabase info
                if supabase_result.get("success"):
                    await self.db.backup_jobs.update_one(
                        {"id": backup_id},
                        {"$set": {
                            "supabase_path": remote_path,
                            "supabase_uploaded": True
                        }}
                    )
            
            await self._log_audit(
                "BACKUP_SUCCESS",
                triggered_by_user_id,
                "backup",
                backup_id,
                {
                    "type": "storage",
                    "filename": filename,
                    "files_count": files_backed_up,
                    "size_bytes": file_size,
                    "supabase_uploaded": supabase_result.get("success") if supabase_result else False
                }
            )
            
            return {
                "id": backup_id,
                "status": "success",
                "filename": filename,
                "path": str(backup_path),
                "size_bytes": file_size,
                "files_backed_up": files_backed_up,
                "supabase_uploaded": supabase_result.get("success") if supabase_result else False,
                "supabase_path": supabase_result.get("remote_path") if supabase_result and supabase_result.get("success") else None
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Storage backup failed: {error_msg}")
            
            await self.db.backup_jobs.update_one(
                {"id": backup_id},
                {"$set": {
                    "status": "failed",
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "error_message": error_msg
                }}
            )
            
            await self._log_audit(
                "BACKUP_FAILED",
                triggered_by_user_id,
                "backup",
                backup_id,
                {"type": "storage", "error": error_msg}
            )
            
            return {
                "id": backup_id,
                "status": "failed",
                "error": error_msg
            }
    
    # ========================================================================
    # FULL BACKUP
    # ========================================================================
    
    async def create_full_backup(
        self,
        triggered_by_user_id: Optional[str] = None,
        retention_class: str = "daily"
    ) -> Dict[str, Any]:
        """Erstellt sowohl Datenbank- als auch Storage-Backup"""
        
        logger.info("Starting full backup (database + storage)")
        
        db_result = await self.create_database_backup(triggered_by_user_id, retention_class)
        storage_result = await self.create_storage_backup(triggered_by_user_id, retention_class)
        
        return {
            "database_backup": db_result,
            "storage_backup": storage_result,
            "status": "success" if db_result.get("status") == "success" and storage_result.get("status") == "success" else "partial_failure"
        }
    
    # ========================================================================
    # DATABASE RESTORE
    # ========================================================================
    
    async def restore_database_backup(
        self,
        backup_id: str,
        triggered_by_user_id: str,
        confirm: bool = False
    ) -> Dict[str, Any]:
        """
        Stellt eine Datenbank aus einem Backup wieder her
        
        WARNUNG: Dies überschreibt bestehende Daten!
        """
        if not confirm:
            return {
                "status": "confirmation_required",
                "message": "Diese Aktion kann bestehende Daten überschreiben. Setzen Sie confirm=true um fortzufahren."
            }
        
        # Find backup job
        backup_job = await self.db.backup_jobs.find_one({"id": backup_id, "backup_type": "database"})
        if not backup_job:
            return {"status": "error", "message": "Backup nicht gefunden"}
        
        backup_path = self.backup_dir / backup_job["storage_path"]
        if not backup_path.exists():
            return {"status": "error", "message": "Backup-Datei nicht gefunden"}
        
        # Create restore job
        restore_id = str(datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"))
        restore_job = {
            "id": restore_id,
            "backup_job_id": backup_id,
            "restore_type": "database",
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "triggered_by_user_id": triggered_by_user_id,
            "error_message": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.restore_jobs.insert_one(restore_job)
        
        await self._log_audit(
            "RESTORE_STARTED",
            triggered_by_user_id,
            "restore",
            restore_id,
            {
                "backup_id": backup_id,
                "backup_date": backup_job.get("created_at"),
                "warning": "Daten werden überschrieben"
            }
        )
        
        try:
            logger.info(f"Starting database restore from: {backup_job['file_name']}")
            
            # Read backup
            with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            metadata = backup_data.pop("_backup_metadata", {})
            
            # Restore each collection
            for collection_name, documents in backup_data.items():
                if not isinstance(documents, list):
                    continue
                
                collection = self.db[collection_name]
                
                # Clear existing data (except backup_jobs and restore_jobs)
                if collection_name not in ["backup_jobs", "restore_jobs"]:
                    await collection.delete_many({})
                    
                    # Insert restored documents
                    if documents:
                        # Convert back from JSON to proper BSON
                        restored_docs = json.loads(
                            json.dumps(documents),
                            object_hook=json_util.object_hook
                        )
                        await collection.insert_many(restored_docs)
                
                logger.info(f"  Restored {len(documents)} documents to {collection_name}")
            
            # Update restore job
            await self.db.restore_jobs.update_one(
                {"id": restore_id},
                {"$set": {
                    "status": "success",
                    "finished_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            
            await self._log_audit(
                "RESTORE_SUCCESS",
                triggered_by_user_id,
                "restore",
                restore_id,
                {
                    "backup_id": backup_id,
                    "collections_restored": list(backup_data.keys()),
                    "backup_date": metadata.get("created_at")
                }
            )
            
            logger.info(f"Database restore completed successfully")
            
            return {
                "status": "success",
                "restore_id": restore_id,
                "backup_id": backup_id,
                "collections_restored": list(backup_data.keys()),
                "backup_date": metadata.get("created_at")
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Database restore failed: {error_msg}")
            
            await self.db.restore_jobs.update_one(
                {"id": restore_id},
                {"$set": {
                    "status": "failed",
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "error_message": error_msg
                }}
            )
            
            await self._log_audit(
                "RESTORE_FAILED",
                triggered_by_user_id,
                "restore",
                restore_id,
                {"backup_id": backup_id, "error": error_msg}
            )
            
            return {"status": "failed", "error": error_msg}
    
    # ========================================================================
    # STORAGE RESTORE
    # ========================================================================
    
    async def restore_storage_backup(
        self,
        backup_id: str,
        triggered_by_user_id: str,
        confirm: bool = False
    ) -> Dict[str, Any]:
        """Stellt Dateien aus einem Storage-Backup wieder her"""
        
        if not confirm:
            return {
                "status": "confirmation_required",
                "message": "Diese Aktion kann bestehende Dateien überschreiben."
            }
        
        backup_job = await self.db.backup_jobs.find_one({"id": backup_id, "backup_type": "storage"})
        if not backup_job:
            return {"status": "error", "message": "Backup nicht gefunden"}
        
        backup_path = self.backup_dir / backup_job["storage_path"]
        if not backup_path.exists():
            return {"status": "error", "message": "Backup-Datei nicht gefunden"}
        
        restore_id = str(datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"))
        
        try:
            upload_dir = Path(__file__).parent / "uploads"
            upload_dir.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(upload_dir)
            
            logger.info(f"Storage restore completed from: {backup_job['file_name']}")
            
            await self._log_audit(
                "RESTORE_SUCCESS",
                triggered_by_user_id,
                "restore",
                restore_id,
                {"backup_id": backup_id, "type": "storage"}
            )
            
            return {"status": "success", "restore_id": restore_id}
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Storage restore failed: {error_msg}")
            
            await self._log_audit(
                "RESTORE_FAILED",
                triggered_by_user_id,
                "restore",
                restore_id,
                {"backup_id": backup_id, "error": error_msg}
            )
            
            return {"status": "failed", "error": error_msg}
    
    # ========================================================================
    # BACKUP MANAGEMENT
    # ========================================================================
    
    async def list_backups(
        self,
        backup_type: Optional[str] = None,
        retention_class: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Listet alle Backups auf"""
        
        query = {}
        if backup_type:
            query["backup_type"] = backup_type
        if retention_class:
            query["retention_class"] = retention_class
        if status:
            query["status"] = status
        
        backups = await self.db.backup_jobs.find(query).sort("created_at", -1).limit(limit).to_list(length=limit)
        
        # Convert ObjectId to string
        for backup in backups:
            backup["_id"] = str(backup.get("_id", ""))
        
        return backups
    
    async def get_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Holt ein einzelnes Backup"""
        backup = await self.db.backup_jobs.find_one({"id": backup_id})
        if backup:
            backup["_id"] = str(backup.get("_id", ""))
        return backup
    
    async def delete_backup(
        self,
        backup_id: str,
        triggered_by_user_id: str
    ) -> Dict[str, Any]:
        """Löscht ein Backup"""
        
        backup = await self.db.backup_jobs.find_one({"id": backup_id})
        if not backup:
            return {"status": "error", "message": "Backup nicht gefunden"}
        
        try:
            # Delete file
            backup_path = self.backup_dir / backup["storage_path"]
            if backup_path.exists():
                backup_path.unlink()
            
            # Delete from DB
            await self.db.backup_jobs.delete_one({"id": backup_id})
            
            await self._log_audit(
                "BACKUP_DELETED",
                triggered_by_user_id,
                "backup",
                backup_id,
                {"filename": backup["file_name"]}
            )
            
            logger.info(f"Backup deleted: {backup['file_name']}")
            
            return {"status": "success", "message": "Backup gelöscht"}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def get_backup_file_path(self, backup_id: str) -> Optional[Path]:
        """Gibt den Pfad zur Backup-Datei zurück"""
        backup = await self.db.backup_jobs.find_one({"id": backup_id})
        if not backup:
            return None
        
        backup_path = self.backup_dir / backup["storage_path"]
        if backup_path.exists():
            return backup_path
        return None
    
    # ========================================================================
    # RETENTION CLEANUP
    # ========================================================================
    
    async def apply_retention_rules(self) -> Dict[str, Any]:
        """Wendet Aufbewahrungsregeln an und löscht alte Backups"""
        
        deleted_daily = 0
        deleted_monthly = 0
        
        now = datetime.now(timezone.utc)
        
        # Delete daily backups older than BACKUP_RETENTION_DAYS
        daily_cutoff = now - timedelta(days=BACKUP_RETENTION_DAYS)
        
        old_daily_backups = await self.db.backup_jobs.find({
            "retention_class": "daily",
            "created_at": {"$lt": daily_cutoff.isoformat()}
        }).to_list(length=None)
        
        for backup in old_daily_backups:
            backup_path = self.backup_dir / backup["storage_path"]
            if backup_path.exists():
                backup_path.unlink()
            await self.db.backup_jobs.delete_one({"id": backup["id"]})
            deleted_daily += 1
        
        # Delete monthly backups older than BACKUP_RETENTION_MONTHS
        monthly_cutoff = now - timedelta(days=BACKUP_RETENTION_MONTHS * 30)
        
        old_monthly_backups = await self.db.backup_jobs.find({
            "retention_class": "monthly",
            "created_at": {"$lt": monthly_cutoff.isoformat()}
        }).to_list(length=None)
        
        for backup in old_monthly_backups:
            backup_path = self.backup_dir / backup["storage_path"]
            if backup_path.exists():
                backup_path.unlink()
            await self.db.backup_jobs.delete_one({"id": backup["id"]})
            deleted_monthly += 1
        
        if deleted_daily > 0 or deleted_monthly > 0:
            logger.info(f"Retention cleanup: deleted {deleted_daily} daily, {deleted_monthly} monthly backups")
            
            await self._log_audit(
                "BACKUP_DELETED",
                None,
                "retention",
                None,
                {
                    "deleted_daily": deleted_daily,
                    "deleted_monthly": deleted_monthly,
                    "reason": "retention_policy"
                }
            )
        
        return {
            "deleted_daily": deleted_daily,
            "deleted_monthly": deleted_monthly
        }
    
    # ========================================================================
    # SYSTEM STATUS
    # ========================================================================
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Gibt den System-Status der Backups zurück"""
        
        # Last successful database backup
        last_db_backup = await self.db.backup_jobs.find_one(
            {"backup_type": "database", "status": "success"},
            sort=[("created_at", -1)]
        )
        
        # Last successful storage backup
        last_storage_backup = await self.db.backup_jobs.find_one(
            {"backup_type": "storage", "status": "success"},
            sort=[("created_at", -1)]
        )
        
        # Last error
        last_error = await self.db.backup_jobs.find_one(
            {"status": "failed"},
            sort=[("created_at", -1)]
        )
        
        # Count backups
        total_backups = await self.db.backup_jobs.count_documents({})
        failed_backups = await self.db.backup_jobs.count_documents({"status": "failed"})
        supabase_backups = await self.db.backup_jobs.count_documents({"supabase_uploaded": True})
        
        # Calculate total size
        all_backups = await self.db.backup_jobs.find({"status": "success"}).to_list(length=None)
        total_size = sum(b.get("file_size_bytes", 0) for b in all_backups)
        
        return {
            "last_database_backup": {
                "date": last_db_backup["created_at"] if last_db_backup else None,
                "filename": last_db_backup["file_name"] if last_db_backup else None,
                "size": last_db_backup["file_size_bytes"] if last_db_backup else 0,
                "supabase_uploaded": last_db_backup.get("supabase_uploaded", False) if last_db_backup else False
            } if last_db_backup else None,
            "last_storage_backup": {
                "date": last_storage_backup["created_at"] if last_storage_backup else None,
                "filename": last_storage_backup["file_name"] if last_storage_backup else None,
                "size": last_storage_backup["file_size_bytes"] if last_storage_backup else 0,
                "supabase_uploaded": last_storage_backup.get("supabase_uploaded", False) if last_storage_backup else False
            } if last_storage_backup else None,
            "last_error": {
                "date": last_error["created_at"] if last_error else None,
                "message": last_error["error_message"] if last_error else None,
                "type": last_error["backup_type"] if last_error else None
            } if last_error else None,
            "total_backups": total_backups,
            "failed_backups": failed_backups,
            "supabase_backups": supabase_backups,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "retention_settings": {
                "daily_retention_days": BACKUP_RETENTION_DAYS,
                "monthly_retention_months": BACKUP_RETENTION_MONTHS
            },
            "supabase_enabled": self.supabase_storage.enabled,
            "next_scheduled_run": "02:00 UTC (täglich)"
        }
    
    # ========================================================================
    # AUDIT LOGGING
    # ========================================================================
    
    async def _log_audit(
        self,
        action: str,
        user_id: Optional[str],
        entity_type: str,
        entity_id: Optional[str],
        details: Dict[str, Any]
    ):
        """Erstellt einen Audit-Log-Eintrag"""
        
        audit_entry = {
            "id": str(uuid.uuid4()) if 'uuid' in dir() else str(datetime.now(timezone.utc).timestamp()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "user_id": user_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            await self.db.audit_logs.insert_one(audit_entry)
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")


# Import uuid for audit logging
import uuid

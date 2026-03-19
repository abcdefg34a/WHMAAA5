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
        """Listet alle Backups in Supabase Storage mit Details"""
        if not self.enabled or not self.client:
            return []
        
        try:
            files = []
            for folder in ['database/daily', 'database/monthly', 'storage/daily', 'storage/monthly']:
                try:
                    folder_files = self.client.storage.from_(SUPABASE_BACKUP_BUCKET).list(folder)
                    for f in folder_files:
                        if f.get('name') and not f.get('name').endswith('/'):
                            # Bestimme Backup-Typ aus Pfad
                            backup_type = 'database' if 'database' in folder else 'storage'
                            retention_class = 'monthly' if 'monthly' in folder else 'daily'
                            
                            # Parse Datum aus Dateiname (z.B. db-backup-2026-03-19-10-00.json.gz)
                            name = f.get('name', '')
                            created_at = f.get('created_at')
                            
                            # Berechne Größe
                            metadata = f.get('metadata', {})
                            size = metadata.get('size', 0) if metadata else 0
                            
                            files.append({
                                "name": name,
                                "path": f"{folder}/{name}",
                                "folder": folder,
                                "backup_type": backup_type,
                                "retention_class": retention_class,
                                "size_bytes": size,
                                "created_at": created_at,
                                "id": f.get('id', name.replace('.', '_'))
                            })
                except Exception as folder_err:
                    logger.warning(f"Fehler beim Auflisten von {folder}: {folder_err}")
                    pass
            
            # Sortiere nach Erstellungsdatum (neueste zuerst)
            files.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return files
            
        except Exception as e:
            logger.error(f"❌ Supabase Auflistung fehlgeschlagen: {e}")
            return []
    
    async def download_backup_to_file(self, remote_path: str, local_path: Path) -> bool:
        """Lädt ein Backup von Supabase herunter und speichert es lokal"""
        if not self.enabled or not self.client:
            return False
        
        try:
            # Download von Supabase
            response = self.client.storage.from_(SUPABASE_BACKUP_BUCKET).download(remote_path)
            
            if response:
                # Stelle sicher, dass das Verzeichnis existiert
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Speichere Datei
                with open(local_path, 'wb') as f:
                    f.write(response)
                
                logger.info(f"✅ Backup von Supabase heruntergeladen: {remote_path} -> {local_path}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Download von Supabase fehlgeschlagen: {e}")
            return False


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
    # BACKUP VERIFIZIERUNG
    # ========================================================================
    
    async def verify_backup(self, backup_id: str) -> Dict[str, Any]:
        """
        Verifiziert ein einzelnes Backup auf Integrität.
        Prüft: Datei existiert, lesbar, Format korrekt, Inhalt valide
        """
        backup_job = await self.db.backup_jobs.find_one({"id": backup_id})
        if not backup_job:
            return {"status": "error", "message": "Backup nicht gefunden", "valid": False}
        
        backup_path = self.backup_dir / backup_job["storage_path"]
        backup_type = backup_job.get("backup_type", "database")
        
        verification_result = {
            "backup_id": backup_id,
            "filename": backup_job.get("file_name"),
            "backup_type": backup_type,
            "checks": [],
            "valid": True,
            "errors": []
        }
        
        # Check 1: Datei existiert
        if not backup_path.exists():
            verification_result["checks"].append({"name": "file_exists", "passed": False})
            verification_result["valid"] = False
            verification_result["errors"].append("Backup-Datei nicht gefunden")
            
            # Update backup job status
            await self.db.backup_jobs.update_one(
                {"id": backup_id},
                {"$set": {"verified": False, "verification_error": "Datei nicht gefunden"}}
            )
            return verification_result
        
        verification_result["checks"].append({"name": "file_exists", "passed": True})
        
        # Check 2: Datei ist nicht leer
        file_size = backup_path.stat().st_size
        if file_size == 0:
            verification_result["checks"].append({"name": "file_not_empty", "passed": False})
            verification_result["valid"] = False
            verification_result["errors"].append("Backup-Datei ist leer")
        else:
            verification_result["checks"].append({"name": "file_not_empty", "passed": True})
        
        # Check 3: Datei ist lesbar und Format korrekt
        try:
            if backup_type == "database":
                # Prüfe gzip und JSON
                with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
                
                verification_result["checks"].append({"name": "gzip_readable", "passed": True})
                verification_result["checks"].append({"name": "json_valid", "passed": True})
                
                # Check 4: Erwartete Struktur (Collections vorhanden)
                expected_collections = ["users", "jobs", "audit_logs"]
                found_collections = [k for k in data.keys() if not k.startswith("_")]
                
                has_data = any(len(data.get(c, [])) > 0 for c in found_collections)
                verification_result["checks"].append({
                    "name": "has_data",
                    "passed": has_data,
                    "details": f"Collections: {found_collections}"
                })
                
                if not has_data:
                    verification_result["errors"].append("Backup enthält keine Daten")
                    verification_result["valid"] = False
                
                # Zähle Dokumente
                doc_counts = {k: len(v) for k, v in data.items() if isinstance(v, list)}
                verification_result["document_counts"] = doc_counts
                verification_result["total_documents"] = sum(doc_counts.values())
                
            else:
                # Storage Backup - prüfe ZIP
                with zipfile.ZipFile(backup_path, 'r') as zf:
                    # Teste Integrität
                    bad_file = zf.testzip()
                    if bad_file:
                        verification_result["checks"].append({"name": "zip_integrity", "passed": False})
                        verification_result["valid"] = False
                        verification_result["errors"].append(f"Korrupte Datei im ZIP: {bad_file}")
                    else:
                        verification_result["checks"].append({"name": "zip_integrity", "passed": True})
                    
                    # Zähle Dateien
                    file_list = zf.namelist()
                    verification_result["file_count"] = len(file_list)
                    verification_result["checks"].append({
                        "name": "has_files",
                        "passed": len(file_list) > 0,
                        "details": f"{len(file_list)} Dateien"
                    })
                    
        except gzip.BadGzipFile:
            verification_result["checks"].append({"name": "gzip_readable", "passed": False})
            verification_result["valid"] = False
            verification_result["errors"].append("Ungültiges GZIP-Format")
        except json.JSONDecodeError as e:
            verification_result["checks"].append({"name": "json_valid", "passed": False})
            verification_result["valid"] = False
            verification_result["errors"].append(f"Ungültiges JSON: {str(e)}")
        except zipfile.BadZipFile:
            verification_result["checks"].append({"name": "zip_readable", "passed": False})
            verification_result["valid"] = False
            verification_result["errors"].append("Ungültiges ZIP-Format")
        except Exception as e:
            verification_result["valid"] = False
            verification_result["errors"].append(f"Unbekannter Fehler: {str(e)}")
        
        # Update backup job mit Verifizierungsstatus
        await self.db.backup_jobs.update_one(
            {"id": backup_id},
            {"$set": {
                "verified": verification_result["valid"],
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "verification_error": verification_result["errors"][0] if verification_result["errors"] else None
            }}
        )
        
        return verification_result
    
    async def verify_all_backups(self) -> Dict[str, Any]:
        """Verifiziert alle Backups und gibt Zusammenfassung zurück"""
        
        backups = await self.db.backup_jobs.find({"status": "success"}).to_list(length=None)
        
        results = {
            "total": len(backups),
            "valid": 0,
            "invalid": 0,
            "errors": [],
            "details": []
        }
        
        for backup in backups:
            result = await self.verify_backup(backup["id"])
            results["details"].append({
                "id": backup["id"],
                "filename": backup.get("file_name"),
                "valid": result["valid"],
                "errors": result.get("errors", [])
            })
            
            if result["valid"]:
                results["valid"] += 1
            else:
                results["invalid"] += 1
                results["errors"].append({
                    "backup_id": backup["id"],
                    "filename": backup.get("file_name"),
                    "error": result.get("errors", ["Unbekannt"])[0]
                })
        
        # Log audit wenn korrupte Backups gefunden
        if results["invalid"] > 0:
            await self._log_audit(
                "BACKUP_VERIFICATION_WARNING",
                None,
                "system",
                None,
                {
                    "total_backups": results["total"],
                    "invalid_count": results["invalid"],
                    "invalid_backups": results["errors"]
                }
            )
            logger.warning(f"Backup verification found {results['invalid']} invalid backups!")
        
        return results
    
    async def get_backup_health(self) -> Dict[str, Any]:
        """Gibt den Gesundheitsstatus aller Backups zurück"""
        
        # Zähle verifizierte und nicht-verifizierte Backups
        total = await self.db.backup_jobs.count_documents({"status": "success"})
        verified_valid = await self.db.backup_jobs.count_documents({"status": "success", "verified": True})
        verified_invalid = await self.db.backup_jobs.count_documents({"status": "success", "verified": False})
        not_verified = total - verified_valid - verified_invalid
        
        # Hole letzte korrupte Backups
        invalid_backups = await self.db.backup_jobs.find(
            {"status": "success", "verified": False}
        ).sort("created_at", -1).limit(5).to_list(length=5)
        
        return {
            "total_backups": total,
            "verified_valid": verified_valid,
            "verified_invalid": verified_invalid,
            "not_verified": not_verified,
            "health_status": "healthy" if verified_invalid == 0 else "warning",
            "invalid_backups": [
                {
                    "id": b["id"],
                    "filename": b.get("file_name"),
                    "error": b.get("verification_error", "Unbekannt")
                }
                for b in invalid_backups
            ]
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
            
            # Helper function to convert $oid and $date fields back to proper BSON types
            def convert_bson_fields(doc):
                """Konvertiert $oid und $date Felder zurück zu BSON-Typen"""
                from bson import ObjectId
                from datetime import datetime
                
                if isinstance(doc, dict):
                    # Check if it's an $oid object
                    if '$oid' in doc and len(doc) == 1:
                        return ObjectId(doc['$oid'])
                    # Check if it's a $date object
                    if '$date' in doc and len(doc) == 1:
                        date_val = doc['$date']
                        if isinstance(date_val, str):
                            return datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                        elif isinstance(date_val, dict) and '$numberLong' in date_val:
                            return datetime.fromtimestamp(int(date_val['$numberLong']) / 1000)
                        return date_val
                    # Recursively convert all fields
                    return {k: convert_bson_fields(v) for k, v in doc.items()}
                elif isinstance(doc, list):
                    return [convert_bson_fields(item) for item in doc]
                return doc
            
            collections_restored = []
            
            # Restore each collection
            for collection_name, documents in backup_data.items():
                if not isinstance(documents, list):
                    continue
                
                collection = self.db[collection_name]
                
                # Clear existing data (except backup_jobs and restore_jobs)
                if collection_name not in ["backup_jobs", "restore_jobs"]:
                    await collection.delete_many({})
                    
                    # Insert restored documents with proper BSON conversion
                    if documents:
                        converted_docs = [convert_bson_fields(doc) for doc in documents]
                        
                        # Insert documents one by one to handle any issues
                        success_count = 0
                        for doc in converted_docs:
                            try:
                                await collection.insert_one(doc)
                                success_count += 1
                            except Exception as e:
                                logger.warning(f"Error inserting document in {collection_name}: {e}")
                        
                        logger.info(f"  Restored {success_count}/{len(documents)} documents to {collection_name}")
                        collections_restored.append(collection_name)
            
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
                    "collections_restored": collections_restored,
                    "backup_date": metadata.get("created_at")
                }
            )
            
            logger.info(f"Database restore completed successfully")
            
            return {
                "status": "success",
                "restore_id": restore_id,
                "backup_id": backup_id,
                "collections_restored": collections_restored,
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
    # CLOUD BACKUP FUNKTIONEN (Supabase)
    # ========================================================================
    
    async def list_cloud_backups(self) -> List[Dict[str, Any]]:
        """Listet alle Backups in Supabase Cloud"""
        if not self.supabase_storage.enabled:
            return []
        
        cloud_backups = await self.supabase_storage.list_backups()
        
        # Prüfe welche auch lokal vorhanden sind
        for backup in cloud_backups:
            local_path = self.backup_dir / backup['path']
            backup['local_available'] = local_path.exists()
        
        return cloud_backups
    
    async def restore_from_cloud(
        self,
        cloud_path: str,
        triggered_by_user_id: str,
        confirm: bool = False
    ) -> Dict[str, Any]:
        """
        Stellt ein Backup direkt von Supabase Cloud wieder her.
        Nützlich wenn lokale Backups verloren gegangen sind.
        """
        if not confirm:
            return {
                "status": "confirmation_required",
                "message": "Diese Aktion lädt das Backup von der Cloud und überschreibt bestehende Daten. Setzen Sie confirm=true um fortzufahren."
            }
        
        if not self.supabase_storage.enabled:
            return {"status": "error", "message": "Supabase Storage ist nicht konfiguriert"}
        
        # Bestimme Backup-Typ aus Pfad
        is_database = 'database' in cloud_path
        backup_type = 'database' if is_database else 'storage'
        
        # Create restore job
        restore_id = str(datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"))
        restore_job = {
            "id": restore_id,
            "backup_job_id": f"cloud_{cloud_path.replace('/', '_')}",
            "restore_type": backup_type,
            "source": "supabase_cloud",
            "cloud_path": cloud_path,
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "triggered_by_user_id": triggered_by_user_id,
            "error_message": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.restore_jobs.insert_one(restore_job)
        
        await self._log_audit(
            "CLOUD_RESTORE_STARTED",
            triggered_by_user_id,
            "restore",
            restore_id,
            {
                "cloud_path": cloud_path,
                "backup_type": backup_type,
                "warning": "Backup wird von Supabase Cloud geladen"
            }
        )
        
        try:
            logger.info(f"Starting cloud restore from: {cloud_path}")
            
            # Temporärer lokaler Pfad
            temp_path = BACKUP_TEMP_DIR / Path(cloud_path).name
            
            # Download von Supabase
            success = await self.supabase_storage.download_backup_to_file(cloud_path, temp_path)
            
            if not success:
                raise Exception("Download von Supabase fehlgeschlagen")
            
            logger.info(f"Cloud backup downloaded to: {temp_path}")
            
            if is_database:
                # Datenbank-Restore
                result = await self._restore_database_from_file(temp_path, triggered_by_user_id, restore_id)
            else:
                # Storage-Restore
                result = await self._restore_storage_from_file(temp_path, triggered_by_user_id, restore_id)
            
            # Cleanup temp file
            if temp_path.exists():
                temp_path.unlink()
            
            # Update restore job
            await self.db.restore_jobs.update_one(
                {"id": restore_id},
                {"$set": {
                    "status": "success" if result.get("status") == "success" else "failed",
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "error_message": result.get("error")
                }}
            )
            
            if result.get("status") == "success":
                await self._log_audit(
                    "CLOUD_RESTORE_SUCCESS",
                    triggered_by_user_id,
                    "restore",
                    restore_id,
                    {
                        "cloud_path": cloud_path,
                        "collections_restored": result.get("collections_restored", [])
                    }
                )
            
            return {
                "status": result.get("status", "error"),
                "restore_id": restore_id,
                "cloud_path": cloud_path,
                "backup_type": backup_type,
                "collections_restored": result.get("collections_restored", []),
                "message": result.get("message", "Wiederherstellung von Cloud abgeschlossen")
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Cloud restore failed: {error_msg}")
            
            await self.db.restore_jobs.update_one(
                {"id": restore_id},
                {"$set": {
                    "status": "failed",
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "error_message": error_msg
                }}
            )
            
            await self._log_audit(
                "CLOUD_RESTORE_FAILED",
                triggered_by_user_id,
                "restore",
                restore_id,
                {"cloud_path": cloud_path, "error": error_msg}
            )
            
            return {"status": "error", "message": error_msg, "restore_id": restore_id}
    
    async def _restore_database_from_file(
        self,
        backup_path: Path,
        triggered_by_user_id: str,
        restore_id: str
    ) -> Dict[str, Any]:
        """Interne Funktion: Stellt Datenbank aus einer Backup-Datei wieder her"""
        try:
            # Read backup
            with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            metadata = backup_data.pop("_backup_metadata", {})
            
            # Helper function to convert $oid and $date fields
            def convert_bson_fields(doc):
                from bson import ObjectId
                from datetime import datetime as dt
                
                if isinstance(doc, dict):
                    if '$oid' in doc and len(doc) == 1:
                        return ObjectId(doc['$oid'])
                    if '$date' in doc and len(doc) == 1:
                        date_val = doc['$date']
                        if isinstance(date_val, str):
                            return dt.fromisoformat(date_val.replace('Z', '+00:00'))
                        elif isinstance(date_val, dict) and '$numberLong' in date_val:
                            return dt.fromtimestamp(int(date_val['$numberLong']) / 1000)
                        return date_val
                    return {k: convert_bson_fields(v) for k, v in doc.items()}
                elif isinstance(doc, list):
                    return [convert_bson_fields(item) for item in doc]
                return doc
            
            collections_restored = []
            
            for collection_name, documents in backup_data.items():
                if not isinstance(documents, list):
                    continue
                
                collection = self.db[collection_name]
                
                if collection_name not in ["backup_jobs", "restore_jobs"]:
                    await collection.delete_many({})
                    
                    if documents:
                        converted_docs = [convert_bson_fields(doc) for doc in documents]
                        
                        success_count = 0
                        for doc in converted_docs:
                            try:
                                await collection.insert_one(doc)
                                success_count += 1
                            except Exception as e:
                                logger.warning(f"Error inserting document: {e}")
                        
                        logger.info(f"  Restored {success_count}/{len(documents)} documents to {collection_name}")
                        collections_restored.append(collection_name)
            
            return {
                "status": "success",
                "collections_restored": collections_restored,
                "message": f"Datenbank wiederhergestellt: {len(collections_restored)} Collections"
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _restore_storage_from_file(
        self,
        backup_path: Path,
        triggered_by_user_id: str,
        restore_id: str
    ) -> Dict[str, Any]:
        """Interne Funktion: Stellt Storage-Dateien aus einem Backup wieder her"""
        try:
            # Extrahiere ZIP-Datei
            storage_dir = self.backup_dir.parent / "storage"
            storage_dir.mkdir(parents=True, exist_ok=True)
            
            files_restored = 0
            with zipfile.ZipFile(backup_path, 'r') as zf:
                for file_info in zf.infolist():
                    if not file_info.is_dir():
                        zf.extract(file_info, storage_dir)
                        files_restored += 1
            
            logger.info(f"Storage restore completed: {files_restored} files")
            
            return {
                "status": "success",
                "files_restored": files_restored,
                "message": f"Storage wiederhergestellt: {files_restored} Dateien"
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    # ========================================================================
    # BACKUP SCHEDULE SETTINGS
    # ========================================================================
    
    async def get_schedule_settings(self) -> Dict[str, Any]:
        """Holt die aktuellen Backup-Zeitplan-Einstellungen"""
        settings = await self.db.backup_settings.find_one({"type": "schedule"})
        
        if not settings:
            # Default-Einstellungen
            return {
                "database_backup_hour": 2,
                "database_backup_minute": 0,
                "storage_backup_hour": 2,
                "storage_backup_minute": 30,
                "monthly_backup_hour": 1,
                "monthly_backup_minute": 0,
                "backup_frequency": "daily",  # daily, every_12h, every_6h
                "retention_days": 30,
                "retention_months": 12,
                "enabled": True
            }
        
        return {
            "database_backup_hour": settings.get("database_backup_hour", 2),
            "database_backup_minute": settings.get("database_backup_minute", 0),
            "storage_backup_hour": settings.get("storage_backup_hour", 2),
            "storage_backup_minute": settings.get("storage_backup_minute", 30),
            "monthly_backup_hour": settings.get("monthly_backup_hour", 1),
            "monthly_backup_minute": settings.get("monthly_backup_minute", 0),
            "backup_frequency": settings.get("backup_frequency", "daily"),
            "retention_days": settings.get("retention_days", 30),
            "retention_months": settings.get("retention_months", 12),
            "enabled": settings.get("enabled", True),
            "updated_at": settings.get("updated_at"),
            "updated_by": settings.get("updated_by")
        }
    
    async def update_schedule_settings(
        self,
        settings: Dict[str, Any],
        updated_by_user_id: str
    ) -> Dict[str, Any]:
        """Aktualisiert die Backup-Zeitplan-Einstellungen"""
        
        # Validierung
        valid_frequencies = ["daily", "every_12h", "every_6h"]
        if settings.get("backup_frequency") and settings["backup_frequency"] not in valid_frequencies:
            return {"status": "error", "message": f"Ungültige Frequenz. Erlaubt: {valid_frequencies}"}
        
        # Stunden validieren (0-23)
        for key in ["database_backup_hour", "storage_backup_hour", "monthly_backup_hour"]:
            if key in settings:
                if not 0 <= settings[key] <= 23:
                    return {"status": "error", "message": f"{key} muss zwischen 0 und 23 sein"}
        
        # Minuten validieren (0-59)
        for key in ["database_backup_minute", "storage_backup_minute", "monthly_backup_minute"]:
            if key in settings:
                if not 0 <= settings[key] <= 59:
                    return {"status": "error", "message": f"{key} muss zwischen 0 und 59 sein"}
        
        # Update-Daten vorbereiten
        update_data = {
            "type": "schedule",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": updated_by_user_id
        }
        
        # Nur übergebene Felder aktualisieren
        allowed_fields = [
            "database_backup_hour", "database_backup_minute",
            "storage_backup_hour", "storage_backup_minute",
            "monthly_backup_hour", "monthly_backup_minute",
            "backup_frequency", "retention_days", "retention_months", "enabled"
        ]
        
        for field in allowed_fields:
            if field in settings:
                update_data[field] = settings[field]
        
        # Upsert in Datenbank
        await self.db.backup_settings.update_one(
            {"type": "schedule"},
            {"$set": update_data},
            upsert=True
        )
        
        # Audit Log
        await self._log_audit(
            "BACKUP_SCHEDULE_UPDATED",
            updated_by_user_id,
            "settings",
            "schedule",
            {"new_settings": update_data}
        )
        
        logger.info(f"Backup schedule updated by user {updated_by_user_id}: {update_data}")
        
        return {
            "status": "success",
            "message": "Zeitplan-Einstellungen aktualisiert. Bitte Server neu starten für sofortige Änderung.",
            "settings": await self.get_schedule_settings()
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

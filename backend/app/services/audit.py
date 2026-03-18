# ============================================================================
# AUDIT SERVICE - Logging für PostgreSQL
# ============================================================================

from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging
import json
from prisma.enums import AuditAction

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger('audit')

class AuditService:
    """Service for audit logging to PostgreSQL"""
    
    def __init__(self, prisma_client):
        self.db = prisma_client
    
    async def log(
        self,
        action: AuditAction,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> dict:
        """Log an audit event to PostgreSQL"""
        
        try:
            # Create audit log entry
            audit_entry = await self.db.auditlog.create(
                data={
                    'action': action,
                    'userId': user_id,
                    'userEmail': user_email,
                    'userName': user_name,
                    'entityType': entity_type,
                    'entityId': entity_id,
                    'details': details if details else None,
                    'ipAddress': ip_address,
                    'userAgent': user_agent
                }
            )
            
            # Also log to file for backup
            audit_logger.info(json.dumps({
                'id': audit_entry.id,
                'action': action.value if hasattr(action, 'value') else str(action),
                'user_id': user_id,
                'user_email': user_email,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'details': details,
                'created_at': audit_entry.createdAt.isoformat()
            }, ensure_ascii=False, default=str))
            
            return {
                'id': audit_entry.id,
                'action': action,
                'created_at': audit_entry.createdAt.isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to create audit log: {e}")
            # Still log to file even if DB fails
            audit_logger.error(json.dumps({
                'action': str(action),
                'user_id': user_id,
                'error': str(e)
            }, ensure_ascii=False))
            return {}
    
    async def get_logs(
        self,
        action: Optional[AuditAction] = None,
        user_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """Get audit logs with filters"""
        
        where = {}
        if action:
            where['action'] = action
        if user_id:
            where['userId'] = user_id
        if entity_type:
            where['entityType'] = entity_type
        if entity_id:
            where['entityId'] = entity_id
        
        logs = await self.db.auditlog.find_many(
            where=where,
            order={'createdAt': 'desc'},
            take=limit,
            skip=offset
        )
        
        return logs
    
    async def count_logs(
        self,
        action: Optional[AuditAction] = None,
        user_id: Optional[str] = None
    ) -> int:
        """Count audit logs with filters"""
        
        where = {}
        if action:
            where['action'] = action
        if user_id:
            where['userId'] = user_id
        
        return await self.db.auditlog.count(where=where)

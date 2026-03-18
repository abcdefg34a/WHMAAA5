# ============================================================================
# DATABASE CONNECTION - Prisma Client für PostgreSQL/Supabase
# ============================================================================

from prisma import Prisma
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)

# Global Prisma client instance
prisma = Prisma()

async def connect_db():
    """Connect to the database"""
    if not prisma.is_connected():
        await prisma.connect()
        logger.info("✅ Prisma Client connected to PostgreSQL")

async def disconnect_db():
    """Disconnect from the database"""
    if prisma.is_connected():
        await prisma.disconnect()
        logger.info("✅ Prisma Client disconnected")

@asynccontextmanager
async def get_db():
    """Context manager for database operations"""
    try:
        if not prisma.is_connected():
            await prisma.connect()
        yield prisma
    finally:
        pass  # Keep connection open for reuse

# Export the prisma client for direct use
db = prisma

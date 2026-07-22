"""
scripts/clear_data.py — Utility to clear all uploaded documents, placements, and clusters.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import shutil
import logging

from database import AsyncSessionLocal
from sqlalchemy import text
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def clear_all_data():
    logger.info("Truncating documents, placements, and clusters tables...")
    async with AsyncSessionLocal() as db:
        await db.execute(text("TRUNCATE TABLE placements, clusters, documents CASCADE;"))
        await db.commit()

    logger.info("Cleaning up temporary stored files...")
    if os.path.exists(settings.TEMP_DIR):
        shutil.rmtree(settings.TEMP_DIR, ignore_errors=True)
    os.makedirs(settings.TEMP_DIR, exist_ok=True)

    logger.info("Successfully cleared all uploaded documents and data!")


if __name__ == "__main__":
    asyncio.run(clear_all_data())

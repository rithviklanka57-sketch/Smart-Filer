import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from database import AsyncSessionLocal
from models import Document
from sqlalchemy import select


async def main():
    async with AsyncSessionLocal() as db:
        docs = (await db.execute(select(Document))).scalars().all()
        print(f"Total Documents in DB: {len(docs)}")
        for d in docs:
            print(f"- {d.filename} | Status: {d.status} | Error: {d.error_message}")


if __name__ == "__main__":
    asyncio.run(main())

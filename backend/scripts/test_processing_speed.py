"""
scripts/test_processing_speed.py — Benchmark full document processing speed.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import asyncio
import logging

from database import AsyncSessionLocal, init_db
from models import User, Document
from services.extraction import extract_text
from services.llm import classify_document
from services.embeddings import embed_text
from services.placement import find_best_placement
from sqlalchemy import select

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# Sample 10th class / Secondary School Certificate document text
SAMPLE_TEXT = """
BOARD OF SECONDARY EDUCATION, TELANGANA STATE, INDIA
SECONDARY SCHOOL CERTIFICATE - REGULAR
CERTIFIED THAT: LANKA SAISUDHA RITHVIK
FATHER'S NAME: LANKA SARATH
MOTHER'S NAME: LANKA GAYATRI LAKSHMI DEVI
ROLL NO: 2322130253
DATE OF BIRTH: 26/06/2007
SCHOOL: NARAYANA OLYMPIAD SCHOOL BAGHAMBERPET HYD
SUBJECTS: TELUGU (A1), ENGLISH (A1), MATHEMATICS (A1), SCIENCE (A1), SOCIAL STUDIES (A1), HINDI (A1)
CGPA: 9.5
DATE OF ISSUE: 10/05/2023
"""


async def run_benchmark():
    await init_db()

    print("\n" + "=" * 60)
    print(" BENCHMARK: SMART FILER DOCUMENT PROCESSING PIPELINE")
    print("=" * 60 + "\n")

    # 1. Text Extraction
    t0 = time.perf_counter()
    extracted = extract_text(SAMPLE_TEXT.encode("utf-8"), "Secondary_School_Certificate.pdf", "application/pdf")
    t1 = time.perf_counter()
    extract_time = (t1 - t0) * 1000
    print(f"  [Step 1] Text Extraction:  {extract_time:6.2f} ms")

    # 2. AI Classification (LLM / Fallback)
    t0 = time.perf_counter()
    classification = classify_document(extracted)
    t1 = time.perf_counter()
    classify_time = (t1 - t0) * 1000
    print(f"  [Step 2] AI Classification: {classify_time:6.2f} ms (Type: {classification.get('doc_type')})")

    # 3. Vector Embedding (Voyage AI)
    t0 = time.perf_counter()
    embed_input = f"{classification.get('summary', '')} {classification.get('suggested_topic', '')} {classification.get('doc_type', '')}"
    embedding = await embed_text(embed_input.strip() or extracted[:200])
    t1 = time.perf_counter()
    embed_time = (t1 - t0) * 1000
    print(f"  [Step 3] Vector Embedding:  {embed_time:6.2f} ms (Dim: {len(embedding) if embedding else 0})")

    # 4. Folder Placement Matching
    t0 = time.perf_counter()
    async with AsyncSessionLocal() as db:
        stmt = select(User).limit(1)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        user_id = user.id if user else None

        if user_id:
            placement = await find_best_placement(db, user_id, embedding, classification.get('summary', ''))
            placement_mode = placement.get("mode")
        else:
            placement_mode = "N/A"
    t1 = time.perf_counter()
    placement_time = (t1 - t0) * 1000
    print(f"  [Step 4] Folder Matching:   {placement_time:6.2f} ms (Mode: {placement_mode})")

    total_time = extract_time + classify_time + embed_time + placement_time
    total_sec = total_time / 1000.0

    print("\n" + "-" * 60)
    print(f"  TOTAL PROCESSING TIME: {total_time:6.2f} ms ({total_sec:.2f} seconds)")
    print("-" * 60)

    if total_sec <= 3.0:
        print(f"\n  [SUCCESS] Processing completed in {total_sec:.2f} seconds (Target: 1-3 seconds)!\n")
    else:
        print(f"\n  [WARNING] Processing took {total_sec:.2f} seconds.\n")


if __name__ == "__main__":
    asyncio.run(run_benchmark())

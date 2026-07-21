"""
services/embeddings.py — Embedding generation via Voyage AI (or compatible endpoint).
"""
import asyncio
import logging
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


async def embed_text(text: str) -> Optional[list[float]]:
    """
    Generate a single embedding vector for the given text.
    Returns None on failure (caller should handle gracefully).
    """
    if not settings.EMBEDDING_API_KEY or not text.strip():
        return None

    payload = {
        "model": settings.EMBEDDING_MODEL,
        "input": [text[:8000]],  # truncate to model limit
    }
    headers = {
        "Authorization": f"Bearer {settings.EMBEDDING_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.EMBEDDING_BASE_URL}/embeddings",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]
    except Exception as e:
        logger.error("Embedding error: %s", e)
        return None


async def embed_texts(texts: list[str]) -> list[Optional[list[float]]]:
    """Embed multiple texts concurrently."""
    tasks = [embed_text(t) for t in texts]
    return await asyncio.gather(*tasks)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)

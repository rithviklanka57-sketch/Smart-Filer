"""
services/llm.py — All Anthropic API calls.
Every call requests and validates structured JSON output.
"""
import json
import logging
from typing import Any

import anthropic

from config import settings

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _call(system: str, user: str, max_tokens: int = 1024) -> str:
    """Raw Anthropic call; returns assistant message text."""
    response = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


def classify_document(extracted_text: str) -> dict[str, Any]:
    """
    Returns structured JSON:
    {
      "doc_type": "invoice | contract | notes | resume | ...",
      "summary": "one or two sentence summary",
      "entities": {"dates": [], "orgs": [], "amounts": []},
      "suggested_topic": "short label"
    }
    """
    system = (
        "You are a document classifier. Given document text, return ONLY valid JSON with no markdown "
        "fences or extra text. Schema:\n"
        '{"doc_type": string, "summary": string, "entities": {"dates": [], "orgs": [], "amounts": []}, '
        '"suggested_topic": string}'
    )
    prompt = f"Classify this document:\n\n{extracted_text[:8000]}"
    raw = _call(system, prompt, max_tokens=512)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("LLM returned non-JSON for classification: %s", raw[:200])
        return {
            "doc_type": "unknown",
            "summary": raw[:300],
            "entities": {"dates": [], "orgs": [], "amounts": []},
            "suggested_topic": "uncategorized",
        }


def generate_clarifying_question(
    doc_summary: str, candidate_folders: list[dict]
) -> dict[str, Any]:
    """
    Returns:
    {
      "question": "Which project is this related to?",
      "options": ["Work/ProjectA", "Work/ProjectB", "Personal"]
    }
    """
    folder_names = [f["path"] or f["name"] for f in candidate_folders[:3]]
    system = (
        "You are a helpful assistant. Given a document summary and candidate folder names, "
        "generate ONE targeted clarifying question with the folder names as options. "
        "Return ONLY valid JSON. Schema: {\"question\": string, \"options\": [string]}"
    )
    prompt = (
        f"Document summary: {doc_summary}\n"
        f"Candidate folders: {json.dumps(folder_names)}\n"
        "Generate one clarifying question."
    )
    raw = _call(system, prompt, max_tokens=256)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"question": "Which folder should this go in?", "options": folder_names}


def propose_folder_name(member_summaries: list[str]) -> dict[str, Any]:
    """
    Returns: {"folder_name": "Tax Documents 2024", "topic_label": "tax documents"}
    """
    system = (
        "You are a file organization assistant. Given summaries of related documents, "
        "propose a short, clear Google Drive folder name and a topic label. "
        "Return ONLY valid JSON. Schema: {\"folder_name\": string, \"topic_label\": string}"
    )
    combined = "\n---\n".join(member_summaries[:10])
    prompt = f"These documents are related:\n{combined}\n\nPropose a folder name."
    raw = _call(system, prompt, max_tokens=128)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"folder_name": "Related Documents", "topic_label": "documents"}


def explain_placement(doc_summary: str, folder_path: str, confidence: float) -> str:
    """Return a short human-readable explanation of why a folder was chosen."""
    system = "You are a helpful assistant. Write one sentence explaining a filing decision. Be concise."
    prompt = (
        f"Document: {doc_summary}\n"
        f"Suggested folder: {folder_path}\n"
        f"Confidence: {confidence:.0%}\n"
        "Why is this a good match? (one sentence)"
    )
    return _call(system, prompt, max_tokens=100).strip()

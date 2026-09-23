"""Persistent dataset for explicitly human-confirmed entity labels."""

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import config
from .merchant_memory import ALLOWED_CATEGORIES, normalize_entity_key
from src.nlp.preprocessing import clean_text

FEEDBACK_FIELDS = [
    "transaction_description", "cleaned_description", "normalized_entity", "entity_type",
    "confirmed_category", "confirmation_source", "confirmed_at",
]


def load_feedback(path: Optional[Path] = None) -> list[dict]:
    feedback_path = Path(path or config.HUMAN_FEEDBACK_PATH)
    if not feedback_path.exists():
        return []
    with feedback_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def append_human_feedback(
    transaction_description: str,
    entity_type: str,
    confirmed_category: str,
    *,
    normalized_entity: Optional[str] = None,
    path: Optional[Path] = None,
) -> bool:
    if confirmed_category not in ALLOWED_CATEGORIES:
        raise ValueError(f"Invalid feedback category: {confirmed_category}")
    entity = normalized_entity or normalize_entity_key(transaction_description)
    rows = load_feedback(path)
    if any(row.get("normalized_entity") == entity and row.get("confirmed_category") == confirmed_category for row in rows):
        return False
    feedback_path = Path(path or config.HUMAN_FEEDBACK_PATH)
    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    has_header = feedback_path.exists() and feedback_path.stat().st_size > 0
    with feedback_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FEEDBACK_FIELDS)
        if not has_header:
            writer.writeheader()
        writer.writerow({
            "transaction_description": transaction_description,
            "cleaned_description": clean_text(transaction_description),
            "normalized_entity": entity,
            "entity_type": entity_type,
            "confirmed_category": confirmed_category,
            "confirmation_source": "human",
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
        })
    return True


def unique_feedback_entity_count(path: Optional[Path] = None) -> int:
    return len({row.get("normalized_entity") for row in load_feedback(path) if row.get("confirmation_source") == "human"})

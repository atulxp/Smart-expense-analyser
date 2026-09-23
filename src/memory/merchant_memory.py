"""JSON-backed human-confirmed merchant/entity mappings."""

import csv
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import config

ALLOWED_CATEGORIES = {
    "Food", "Shopping", "Travel", "Entertainment", "Health", "Utilities", "P2P", "Unknown"
}


def normalize_entity_key(description: str, merchant: Optional[str] = None) -> str:
    """Conservatively normalize one entity; never fuzzy-merges similar names."""
    candidate = merchant if merchant and merchant != "Unknown" else description
    candidate = re.sub(r"[^a-zA-Z0-9 ]+", " ", str(candidate).lower())
    return " ".join(candidate.strip().split())


def load_memory(path: Optional[Path] = None) -> Dict[str, dict]:
    memory_path = Path(path or config.MERCHANT_MEMORY_PATH)
    if not memory_path.exists():
        return {}
    try:
        payload = json.loads(memory_path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    mappings = payload.get("mappings", payload) if isinstance(payload, dict) else {}
    return mappings if isinstance(mappings, dict) else {}


def get_memory_category(entity_key: str, path: Optional[Path] = None) -> Optional[str]:
    mapping = load_memory(path).get(entity_key)
    if not isinstance(mapping, dict):
        return None
    category = mapping.get("category")
    return category if category in ALLOWED_CATEGORIES else None


def save_memory_mapping(
    entity_key: str,
    category: str,
    *,
    entity_type: Optional[str] = None,
    example: Optional[str] = None,
    notes: Optional[str] = None,
    path: Optional[Path] = None,
    audit_path: Optional[Path] = None,
) -> dict:
    if not entity_key or category not in ALLOWED_CATEGORIES:
        raise ValueError(f"Invalid entity mapping: {entity_key!r} -> {category!r}")
    memory_path = Path(path or config.MERCHANT_MEMORY_PATH)
    audit_file = Path(audit_path or config.MERCHANT_MEMORY_AUDIT_PATH)
    mappings = load_memory(memory_path)
    now = datetime.now(timezone.utc).isoformat()
    old = mappings.get(entity_key)
    record = {
        "normalized_entity": entity_key,
        "category": category,
        "confirmation_source": "human",
        "created_at": old.get("created_at", now) if isinstance(old, dict) else now,
        "updated_at": now,
    }
    if entity_type:
        record["entity_type"] = entity_type
    if example:
        record["original_examples"] = [example]
        if isinstance(old, dict):
            record["original_examples"] = sorted(set(old.get("original_examples", []) + [example]))
    if notes:
        record["notes"] = notes
    mappings[entity_key] = record
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=memory_path.parent, delete=False) as handle:
        json.dump({"mappings": mappings}, handle, indent=2)
        temporary_path = Path(handle.name)
    os.replace(temporary_path, memory_path)

    audit_file.parent.mkdir(parents=True, exist_ok=True)
    action = "UPDATE" if isinstance(old, dict) else "CREATE"
    has_header = audit_file.exists() and audit_file.stat().st_size > 0
    with audit_file.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["normalized_entity", "old_category", "new_category", "action", "confirmation_source", "timestamp"])
        if not has_header:
            writer.writeheader()
        writer.writerow({
            "normalized_entity": entity_key,
            "old_category": old.get("category", "") if isinstance(old, dict) else "",
            "new_category": category,
            "action": action,
            "confirmation_source": "human",
            "timestamp": now,
        })
    return record

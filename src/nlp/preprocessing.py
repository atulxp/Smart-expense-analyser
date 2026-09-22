"""Lightweight, merchant-preserving text preprocessing."""

import re
from typing import Dict

_STOP_WORDS = {
    "paid", "payment", "to", "from", "via", "for", "the", "and",
    "order", "purchase", "transaction", "ref", "reference", "status",
}
_PAYMENT_METHODS = {"upi", "imps", "neft", "rtgs", "card", "pos", "bank"}


def preprocess_description(description: str) -> Dict[str, object]:
    """Return normalized text plus useful metadata without erasing merchant terms."""
    if not isinstance(description, str) or not description.strip():
        return {"cleaned_text": "", "tokens": [], "payment_method": None}

    text = description.lower()
    payment_method = next((token.upper() for token in _PAYMENT_METHODS if re.search(rf"\b{token}\b", text)), None)
    text = re.sub(r"\b\d{4,}\b", " ", text)
    text = re.sub(r"\b(?:order|ref|txn|transaction|invoice)[-_]?[a-z]*\d+\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens = [token for token in text.split() if token not in _STOP_WORDS and token not in _PAYMENT_METHODS]
    return {
        "cleaned_text": " ".join(tokens),
        "tokens": tokens,
        "payment_method": payment_method,
    }


def clean_text(description: str) -> str:
    """Convenience wrapper used by the classifier."""
    return str(preprocess_description(description)["cleaned_text"])

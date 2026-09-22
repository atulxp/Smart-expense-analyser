"""Optional, cached public web enrichment with graceful offline behavior."""

import json
import logging
import os
from functools import lru_cache
from urllib.parse import quote
from urllib.request import Request, urlopen

LOGGER = logging.getLogger(__name__)

_TYPE_TO_CATEGORY = {
    "restaurant": "Food", "food": "Food", "grocery": "Shopping", "supermarket": "Shopping",
    "retail": "Shopping", "shopping": "Shopping", "taxi": "Travel", "transport": "Travel",
    "travel": "Travel", "pharmacy": "Health", "hospital": "Health", "health": "Health",
    "subscription": "Entertainment", "entertainment": "Entertainment", "utility": "Utilities",
}


@lru_cache(maxsize=256)
def enrich_merchant(merchant: str, timeout: int = 5):
    """Query DuckDuckGo's public instant-answer endpoint when explicitly enabled.

    It is opt-in through WEB_ENRICHMENT_LIVE=1 so normal runs remain offline-safe.
    """
    if not merchant or merchant == "Unknown" or os.getenv("WEB_ENRICHMENT_LIVE") != "1":
        return {"merchant_type": None, "category": None, "source": None, "confidence": 0.0, "enriched": False}
    try:
        url = "https://api.duckduckgo.com/?format=json&no_html=1&skip_disambig=1&q=" + quote(merchant)
        request = Request(url, headers={"User-Agent": "SmartExpenseAnalyzer/1.0"})
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        text = " ".join([payload.get("AbstractText", ""), payload.get("Heading", "")]).lower()
        merchant_type = next((kind for kind in _TYPE_TO_CATEGORY if kind in text), None)
        if not merchant_type:
            return {"merchant_type": None, "category": None, "source": None, "confidence": 0.0, "enriched": False}
        return {
            "merchant_type": merchant_type.title(), "category": _TYPE_TO_CATEGORY[merchant_type],
            "source": "DuckDuckGo Instant Answer", "confidence": 0.72, "enriched": True,
        }
    except Exception as exc:
        LOGGER.warning("Merchant enrichment unavailable for %s: %s", merchant, type(exc).__name__)
        return {"merchant_type": None, "category": None, "source": None, "confidence": 0.0, "enriched": False}

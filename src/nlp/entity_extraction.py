"""Practical merchant and payment metadata extraction for statements."""

import re
from typing import Dict

from .preprocessing import preprocess_description

_KNOWN_MERCHANTS = {
    "swiggy": "Swiggy", "zomato": "Zomato", "uber": "Uber", "ola": "Ola",
    "rapido": "Rapido", "amazon": "Amazon", "flipkart": "Flipkart",
    "netflix": "Netflix", "spotify": "Spotify", "apollo": "Apollo Pharmacy",
    "mcdonald": "McDonald's", "starbucks": "Starbucks", "indigo": "IndiGo",
    "amzn": "Amazon", "maxhealthcare": "Max Healthcare",
    "jiotv": "JioTV", "jiohotstar": "JioHotstar", "electricity": "Electricity", "pharmacy": "Pharmacy",
    "ajio": "AJIO", "youtube": "YouTube", "airtel": "Airtel", "blinkit": "Blinkit",
    "mumbaimetro": "Mumbai Metro", "mmrcl": "Mumbai Metro", "indianrailway": "Indian Railway",
    "irctc": "IRCTC", "chalo": "Chalo", "cmpppiwalletload": "Wallet Service",
}
_NOISE = {
    "upi", "imps", "neft", "rtgs", "card", "pos", "payment", "paid", "to",
    "from", "order", "purchase", "food", "trip", "bill", "subscription",
    "delivery", "online", "technologies", "india", "booking", "service",
}
_BUSINESS_SIGNALS = {"mart", "store", "shop", "market", "supermarket", "restaurant", "cafe", "clinic", "hospital", "pharmacy"}
_SERVICE_SIGNALS = {
    "metro", "railway", "rail", "ticket", "wallet", "dairy", "bakery", "grocery", "transport",
    "bus", "travel", "food", "juice", "trader", "traders", "service", "services", "solution",
    "solutions", "club", "youtube", "ajio", "rapido", "mmrcl", "chalo", "hospital", "clinic",
    "restaurant", "cafe", "pharmacy", "school", "college", "fuel", "petrol", "recharge",
    "medical", "burger", "chicken", "idli", "bookmyshow", "samosa", "sweet", "sweets", "general",
}
_UNKNOWN_HINTS = {"unknown", "merchant", "xyz"}
_P2P_TERMS = {"transfer", "transferred", "sent", "received", "repayment", "repay", "personal"}
_BUSINESS_SUFFIXES = {"pvt", "ltd", "limited", "enterprise", "enterprises", "company", "corp", "corporation", "agency"}
_FOOD_SIGNALS = {"food", "bakery", "cafe", "restaurant", "restaurants", "hotel", "caterers", "catering", "shawarma", "snacks", "samosa", "chicken", "idli", "juice", "dairy"}
_TRANSPORT_SIGNALS = {"railway", "metro", "airlines", "transport", "bus", "travel", "ticket", "petrol", "fuel"}
_HEALTH_SIGNALS = {"pharmacy", "medical", "hospital", "clinic", "doctor", "health", "dental"}
_TELECOM_SIGNALS = {"mobile", "telecom", "recharge", "airtel", "jio", "phone"}


def extract_entities(description: str) -> Dict[str, object]:
    """Extract a conservative merchant name and payment method from transaction text."""
    metadata = preprocess_description(description)
    lowered = str(description or "").lower()
    for key, display_name in sorted(_KNOWN_MERCHANTS.items(), key=lambda item: len(item[0]), reverse=True):
        if key in re.sub(r"[^a-z0-9]", "", lowered):
            entity_type = "SERVICE" if key in {"mumbaimetro", "mmrcl", "indianrailway", "irctc", "chalo", "cmpppiwalletload"} else "MERCHANT"
            return {"merchant": display_name, "search_candidate": display_name, "location": _extract_location(description), "payment_method": metadata["payment_method"], "entity_type": entity_type}

    tokens = [token for token in metadata["tokens"] if token not in _NOISE and not token.isdigit()]
    compact = re.sub(r"[^a-z0-9]", "", lowered)
    signals = [signal for signal in (_SERVICE_SIGNALS | _BUSINESS_SIGNALS) if signal in compact]
    all_tokens = set(tokens)
    suffix_indicators = {suffix for suffix in _BUSINESS_SUFFIXES if suffix in compact}
    business_indicators = sorted(set(signals) | suffix_indicators | (all_tokens & _FOOD_SIGNALS) | (all_tokens & _TRANSPORT_SIGNALS) | (all_tokens & _HEALTH_SIGNALS) | (all_tokens & _TELECOM_SIGNALS))
    compact_business_indicators = {signal for signal in (_FOOD_SIGNALS | _TRANSPORT_SIGNALS | _HEALTH_SIGNALS | _TELECOM_SIGNALS) if signal in compact}
    business_indicators = sorted(set(business_indicators) | compact_business_indicators)
    merchant = _pretty_candidate(description) if signals or business_indicators else "Unknown"
    if merchant != "Unknown":
        entity_type = "SERVICE" if any(signal in {"metro", "railway", "rail", "ticket", "transport", "bus", "travel", "wallet", "service", "services", "solution", "solutions", "recharge"} for signal in signals) else "MERCHANT"
    elif _looks_like_person(description, tokens) and not any(hint in compact for hint in _UNKNOWN_HINTS):
        entity_type = "PERSON"
    else:
        entity_type = "UNKNOWN"
    p2p_evidence = {
        "person_entity": entity_type == "PERSON",
        "payment_method": metadata["payment_method"] in {"UPI", "IMPS", "NEFT", "RTGS"},
        "transfer_language": any(term in tokens for term in _P2P_TERMS),
        "business_indicators": business_indicators,
        "positive": entity_type == "PERSON" and not business_indicators and (
            metadata["payment_method"] in {"UPI", "IMPS", "NEFT", "RTGS"}
            or any(term in tokens for term in _P2P_TERMS)
        ),
    }
    return {"merchant": merchant, "search_candidate": _pretty_candidate(description) if merchant == "Unknown" else merchant, "location": _extract_location(description), "payment_method": metadata["payment_method"], "entity_type": entity_type, "business_indicators": business_indicators, "p2p_evidence": p2p_evidence}


def entity_feature_tokens(description: str) -> list[str]:
    """Return a small explainable token set for the existing text feature matrix."""
    metadata = preprocess_description(description)
    entities = extract_entities(description)
    tokens = set(metadata["tokens"])
    compact = re.sub(r"[^a-z0-9]", "", str(description or "").lower())
    features = [f"ENTITY_{entities['entity_type']}"]
    indicators = set(entities.get("business_indicators", []))
    if indicators & _BUSINESS_SUFFIXES:
        features.append("HAS_BUSINESS_SUFFIX")
    if indicators & _FOOD_SIGNALS:
        features.append("HAS_FOOD_BUSINESS_SIGNAL")
    if indicators & _TRANSPORT_SIGNALS:
        features.append("HAS_TRANSPORT_SIGNAL")
    if indicators & _HEALTH_SIGNALS:
        features.append("HAS_HEALTH_BUSINESS_SIGNAL")
    if indicators & _TELECOM_SIGNALS:
        features.append("HAS_TELECOM_SIGNAL")
    if indicators & {"store", "stores", "shop", "mart", "market", "supermarket"}:
        features.append("HAS_STORE_SIGNAL")
    if indicators & {"service", "services", "solution", "solutions", "technology", "technologies"}:
        features.append("HAS_SERVICE_SIGNAL")
    if metadata["payment_method"]:
        features.append(f"PAYMENT_{metadata['payment_method']}")
    if any(term in tokens for term in _P2P_TERMS):
        features.append("HAS_TRANSFER_LANGUAGE")
    if re.search(r"(?:^|[^a-z0-9])upi(?:[^a-z0-9]|$)", str(description or "").lower()):
        features.append("HAS_UPI_MARKER")
    if re.search(r"@[a-z0-9._-]+", str(description or "").lower()):
        features.append("HAS_VPA_PATTERN")
    return features


def _pretty_candidate(description: str) -> str:
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", str(description or ""))
    text = re.sub(r"[^A-Za-z0-9 ]+", " ", text)
    text = re.sub(r"\b\d{2,}\b", " ", text)
    text = re.sub(r"\b(?:upi|pos|payment|order|invoice|ref|txn)\b", " ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip().title() or "Unknown"


def _looks_like_person(description: str, tokens: list) -> bool:
    text = str(description or "").strip()
    if any(char.isdigit() for char in text) or not text:
        return False
    return len(tokens) <= 3 and 4 <= len(re.sub(r"[^A-Za-z]", "", text)) <= 35


def _extract_location(description: str) -> str:
    common_locations = ("mumbai", "delhi", "bengaluru", "bangalore", "pune", "hyderabad", "chennai")
    lowered = str(description or "").lower()
    return next((location.title() for location in common_locations if location in lowered), "Unknown")

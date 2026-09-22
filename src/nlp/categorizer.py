"""Hybrid baseline, NLP, and optional web categorization."""

import logging
from functools import lru_cache
from typing import Dict

import pandas as pd

import config
from .classifier import ExpenseClassifier
from .entity_extraction import extract_entities
from .preprocessing import preprocess_description
from src.web.merchant_enrichment import enrich_merchant

LOGGER = logging.getLogger(__name__)
UNKNOWN_CATEGORY = "Unknown"
P2P_CATEGORY = "P2P"


def _canonical_category(category: str) -> str:
    return UNKNOWN_CATEGORY if category in {"P2P / Misc", "Others", None} else category


def _explicit_categories(description: str) -> set:
    text = str(description or "").lower()
    return {
        category
        for category, category_config in config.CATEGORIES.items()
        if category != "Others" and any(keyword in text for keyword in category_config["keywords"])
    }


@lru_cache(maxsize=1)
def get_classifier():
    try:
        return ExpenseClassifier(config.TRAINING_DATA_PATH)
    except Exception as exc:
        LOGGER.warning("NLP model unavailable; using keyword categorization: %s", type(exc).__name__)
        return None


def categorize_transaction_enhanced(description: str) -> Dict[str, object]:
    baseline = _canonical_category(config.get_category(description))
    entities = extract_entities(description)
    result = {
        "Merchant": entities["merchant"],
        "Search_Candidate": entities["search_candidate"],
        "Entity_Type": entities["entity_type"],
        "Location": entities["location"],
        "Payment_Method": entities["payment_method"] or "Unknown",
        "Transaction_Entity_Type": entities["entity_type"],
        "Business_Indicators": ", ".join(entities.get("business_indicators", [])),
        "P2P_Evidence": entities.get("p2p_evidence", {}),
        "P2P_Evidence_Positive": bool(entities.get("p2p_evidence", {}).get("positive")),
        "Baseline_Category": baseline,
        "NLP_Category": UNKNOWN_CATEGORY,
        "Final_Category": baseline,
        "Category_Confidence": 0.0,
        "Categorization_Method": "KEYWORD" if baseline != UNKNOWN_CATEGORY else "ABSTAIN",
        "Merchant_Type": None,
        "Web_Source": None,
        "Web_Confidence": 0.0,
        "Web_Enriched": False,
        "Preprocessed_Text": preprocess_description(description)["cleaned_text"],
    }
    if result["P2P_Evidence_Positive"]:
        result["NLP_Category"] = P2P_CATEGORY
        result["Final_Category"] = P2P_CATEGORY
        result["Categorization_Method"] = "P2P_EVIDENCE"
        return result
    classifier = get_classifier() if config.NLP_ENABLED else None
    if classifier:
        prediction = classifier.predict(description)
        result["NLP_Category"] = _canonical_category(prediction["category"])
        result["Category_Confidence"] = prediction["confidence"]
        if prediction["confidence"] >= config.ML_CONFIDENCE_THRESHOLD:
            explicit_categories = _explicit_categories(description)
            if (
                baseline != UNKNOWN_CATEGORY
                and prediction["category"] != baseline
                and prediction["category"] not in explicit_categories
            ):
                return result
            if prediction["category"] != P2P_CATEGORY and prediction["category"] != "P2P / Misc":
                result["Final_Category"] = prediction["category"]
            else:
                result["Final_Category"] = UNKNOWN_CATEGORY
            result["Categorization_Method"] = "ML"
            return result

    if config.WEB_ENRICHMENT_ENABLED and result["Transaction_Entity_Type"] in {"MERCHANT", "SERVICE", "UNKNOWN"}:
        candidate = result["Search_Candidate"]
        web_result = enrich_merchant(candidate, config.WEB_ENRICHMENT_TIMEOUT)
        result.update({
            "Merchant_Type": web_result["merchant_type"], "Web_Source": web_result["source"],
            "Web_Confidence": web_result["confidence"], "Web_Enriched": web_result["enriched"],
        })
        if web_result["enriched"]:
            result["Final_Category"] = web_result["category"]
            result["Category_Confidence"] = web_result["confidence"]
            result["Categorization_Method"] = "WEB"
            return result

    result["Final_Category"] = baseline if baseline != UNKNOWN_CATEGORY else UNKNOWN_CATEGORY
    return result


def categorize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Add transparent categorization columns while retaining all input columns."""
    if df.empty or "Description" not in df.columns:
        return df.copy()
    enriched = df["Description"].apply(categorize_transaction_enhanced).apply(pd.Series)
    result = pd.concat([df.reset_index(drop=True), enriched.reset_index(drop=True)], axis=1)
    result["Category"] = result["Final_Category"]
    return result

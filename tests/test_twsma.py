import pandas as pd

import config
from app import parse_transactions
from src.analytics.evaluation import comparison_metrics
from src.nlp.categorizer import categorize_dataframe, categorize_transaction_enhanced
from src.nlp.entity_extraction import extract_entities
from src.nlp.entity_extraction import entity_feature_tokens
from src.nlp.preprocessing import preprocess_description
from src.web.merchant_enrichment import enrich_merchant


def test_preprocessing_removes_ids_and_keeps_merchant():
    result = preprocess_description("UPI/123456/SWIGGY/ORDER123")
    assert result["cleaned_text"] == "swiggy"
    assert result["payment_method"] == "UPI"


def test_merchant_extraction_known_and_unknown():
    assert extract_entities("UPI/12345/SWIGGY/FOOD ORDER/MUMBAI")["merchant"] == "Swiggy"
    assert extract_entities("UPI/123456/RAHUL")["merchant"] == "Unknown"
    assert extract_entities("MUMBAIMETRO")["entity_type"] == "SERVICE"
    assert extract_entities("DHARMENDRASINGH")["entity_type"] == "PERSON"
    assert extract_entities("XYZ MART INVOICE 8821")["entity_type"] == "MERCHANT"
    assert extract_entities("TIWARIENTERPRISE")["entity_type"] == "MERCHANT"
    assert extract_entities("BundlTechnologiespvtLtd")["entity_type"] == "MERCHANT"


def test_classifier_categorizes_representative_descriptions():
    assert categorize_transaction_enhanced("UPI-SWIGGY-ORDER123")["Final_Category"] == "Food"
    assert categorize_transaction_enhanced("AMAZON INDIA PURCHASE")["Final_Category"] == "Shopping"
    assert categorize_transaction_enhanced("AMZN INDIA ORDER")["Final_Category"] == "Shopping"
    assert categorize_transaction_enhanced("INDIANRAILWAYTICKETING")["Final_Category"] == "Travel"
    assert "ENTITY_MERCHANT" in entity_feature_tokens("TIWARIENTERPRISE")
    assert "HAS_BUSINESS_SUFFIX" in entity_feature_tokens("BundlTechnologiespvtLtd")


def test_baseline_protection_keeps_ambiguous_store_match():
    result = categorize_transaction_enhanced("BAKERYGENERALSTORE")
    assert result["Final_Category"] == "Shopping"
    assert result["Categorization_Method"] == "KEYWORD"


def test_confidence_threshold_is_used(monkeypatch):
    monkeypatch.setattr(config, "ML_CONFIDENCE_THRESHOLD", 0.99)
    result = categorize_transaction_enhanced("UPI-SWIGGY-ORDER123")
    assert result["Categorization_Method"] in {"KEYWORD", "FALLBACK", "WEB"}


def test_empty_description_falls_back():
    result = categorize_transaction_enhanced("")
    assert result["Final_Category"] == "Unknown"
    assert result["Category_Confidence"] == 0.0


def test_p2p_requires_positive_transfer_evidence():
    person = categorize_transaction_enhanced("RAHUL SHARMA")
    transfer = categorize_transaction_enhanced("UPI PAYMENT TO RAHUL")
    assert person["Final_Category"] == "Unknown"
    assert person["P2P_Evidence_Positive"] is False
    assert transfer["Final_Category"] == "P2P"
    assert transfer["P2P_Evidence_Positive"] is True


def test_web_failure_is_non_fatal(monkeypatch):
    monkeypatch.setenv("WEB_ENRICHMENT_LIVE", "1")
    monkeypatch.setattr("src.web.merchant_enrichment.urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError()))
    result = enrich_merchant("XYZ Unknown Merchant", timeout=1)
    assert result["enriched"] is False


def test_ocr_style_gpay_transaction_line_is_parsed():
    sample = (
        "02Oct2,025 PaitdoPunjSaibnFdoodCsolaNbaavy ₹77\n"
        "12:P2M0 UPTIransaIcDt5:i6o4n163485045\n"
        "PaibdyStaBtaenokfInd9i6a20\n"
    )
    result = parse_transactions(sample)
    assert len(result) == 1
    assert result[0]["Date"] == "2025-10-02"
    assert result[0]["Description"] == "PaitdoPunjSaibnFdoodCsolaNbaavy"
    assert result[0]["Amount"] == "77"


def test_dataframe_and_comparison_metrics():
    frame = categorize_dataframe(pd.DataFrame({"Description": ["UPI-SWIGGY-ORDER123", "UPI/123456/RAHUL"]}))
    metrics = comparison_metrics(frame)
    assert metrics["total_transactions"] == 2
    assert {"Baseline_Category", "NLP_Category", "Final_Category", "Merchant", "Web_Enriched"}.issubset(frame.columns)

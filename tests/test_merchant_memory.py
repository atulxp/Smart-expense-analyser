import json

import pandas as pd
import pytest

import config
from src.memory.merchant_memory import get_memory_category, load_memory, normalize_entity_key, save_memory_mapping
from src.memory.human_feedback import append_human_feedback, load_feedback, unique_feedback_entity_count
from src.memory.review_queue import build_review_queue
from src.nlp.categorizer import categorize_transaction_enhanced, get_classifier
from scripts.retrain_from_feedback import retrain_from_feedback


def test_empty_memory_uses_normal_pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MERCHANT_MEMORY_PATH", tmp_path / "memory.json")
    monkeypatch.setattr(config, "MERCHANT_MEMORY_AUDIT_PATH", tmp_path / "audit.csv")
    monkeypatch.setattr(config, "WEB_ENRICHMENT_ENABLED", False)
    assert categorize_transaction_enhanced("DHARMENDRASINGH")["Final_Category"] == "Unknown"


def test_human_mapping_takes_precedence_and_persists(tmp_path, monkeypatch):
    memory_path = tmp_path / "memory.json"
    audit_path = tmp_path / "audit.csv"
    monkeypatch.setattr(config, "MERCHANT_MEMORY_PATH", memory_path)
    monkeypatch.setattr(config, "MERCHANT_MEMORY_AUDIT_PATH", audit_path)
    monkeypatch.setattr(config, "WEB_ENRICHMENT_ENABLED", False)
    key = normalize_entity_key("DHARMENDRASINGH")
    save_memory_mapping(key, "P2P", entity_type="PERSON", example="DHARMENDRASINGH")
    result = categorize_transaction_enhanced("DHARMENDRASINGH")
    assert result["Final_Category"] == "P2P"
    assert result["Categorization_Method"] == "MERCHANT_MEMORY"
    assert result["NLP_Category"] == "Unknown"
    assert get_memory_category(key) == "P2P"
    assert "CREATE" in audit_path.read_text()
    assert load_memory(memory_path)[key]["confirmation_source"] == "human"


def test_human_unknown_and_update_are_audited(tmp_path):
    memory_path = tmp_path / "memory.json"
    audit_path = tmp_path / "audit.csv"
    key = normalize_entity_key("CMPPPIWalletLoad", "Wallet Service")
    save_memory_mapping(key, "Unknown", path=memory_path, audit_path=audit_path)
    save_memory_mapping(key, "Shopping", path=memory_path, audit_path=audit_path)
    assert get_memory_category(key, memory_path) == "Shopping"
    audit = audit_path.read_text()
    assert "CREATE" in audit and "UPDATE" in audit


def test_invalid_category_rejected(tmp_path):
    with pytest.raises(ValueError):
        save_memory_mapping("entity", "Food-ish", path=tmp_path / "memory.json", audit_path=tmp_path / "audit.csv")


def test_review_queue_is_pending_and_frequency_ordered(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MERCHANT_REVIEW_QUEUE_PATH", tmp_path / "queue.csv")
    frame = pd.DataFrame({
        "Description": ["ALICE", "ALICE", "BOB"],
        "Merchant": ["Unknown", "Unknown", "Unknown"],
        "Entity_Type": ["PERSON", "PERSON", "PERSON"],
        "Final_Category": ["Unknown", "Unknown", "Unknown"],
        "Category_Confidence": [0.8, 0.8, 0.4],
    })
    queue = build_review_queue(frame, limit=2)
    assert queue.iloc[0]["normalized_entity"] == "alice"
    assert set(queue["review_status"]) == {"PENDING"}
    assert (tmp_path / "queue.csv").exists()


def test_human_feedback_is_deduplicated_and_persistent(tmp_path):
    path = tmp_path / "human_feedback.csv"
    assert append_human_feedback("DHARMENDRASINGH", "PERSON", "P2P", path=path) is True
    assert append_human_feedback("DHARMENDRASINGH", "PERSON", "P2P", path=path) is False
    assert unique_feedback_entity_count(path) == 1
    assert load_feedback(path)[0]["confirmation_source"] == "human"


def test_feedback_invalid_category_rejected(tmp_path):
    with pytest.raises(ValueError):
        append_human_feedback("entity", "MERCHANT", "Not a category", path=tmp_path / "feedback.csv")


def test_retraining_waits_for_minimum_feedback(tmp_path, monkeypatch):
    import scripts.retrain_from_feedback as retraining

    retraining.REPORT_PATH = tmp_path / "training_report.json"
    retraining.COMPARISON_PATH = tmp_path / "comparison.json"
    feedback_path = tmp_path / "feedback.csv"
    monkeypatch.setattr(config, "HUMAN_FEEDBACK_PATH", feedback_path)
    append_human_feedback("DHARMENDRASINGH", "PERSON", "P2P", path=feedback_path)
    report = retrain_from_feedback(feedback_path=feedback_path, minimum=20)
    assert report["status"] == "NOT_READY"
    assert not (tmp_path / "model_phase4_candidate.joblib").exists()


def test_twenty_feedback_examples_allow_candidate_without_promotion(tmp_path):
    import scripts.retrain_from_feedback as retraining

    retraining.REPORT_PATH = tmp_path / "training_report.json"
    retraining.COMPARISON_PATH = tmp_path / "comparison.json"
    feedback_path = tmp_path / "feedback.csv"
    audit_categories = ["P2P", "Food", "Shopping", "Travel", "Entertainment", "Health", "Utilities", "Unknown"]
    for index in range(20):
        append_human_feedback(f"HUMAN ENTITY {index}", "MERCHANT", audit_categories[index % len(audit_categories)], path=feedback_path)
    candidate_path = tmp_path / "candidate.joblib"
    report = retrain_from_feedback(feedback_path=feedback_path, candidate_path=candidate_path, minimum=20)
    assert report["status"] == "CANDIDATE_READY"
    assert candidate_path.exists()

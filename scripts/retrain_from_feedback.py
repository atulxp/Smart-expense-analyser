"""Batch-train a Phase 4 candidate from explicit human feedback only."""

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config
from src.analytics.evaluation import evaluate_seed_dataset, evaluate_unseen_merchants
from src.memory.human_feedback import load_feedback, unique_feedback_entity_count
from src.nlp.classifier import ExpenseClassifier

REPORT_PATH = ROOT / "reports" / "phase4_training_report.json"
COMPARISON_PATH = ROOT / "reports" / "phase4_model_comparison.json"


def validated_feedback(path=None) -> pd.DataFrame:
    rows = load_feedback(path)
    valid = {"Food", "Shopping", "Travel", "Entertainment", "Health", "Utilities", "P2P", "Unknown"}
    accepted = [row for row in rows if row.get("confirmation_source") == "human" and row.get("confirmed_category") in valid and row.get("normalized_entity")]
    frame = pd.DataFrame(accepted)
    if frame.empty:
        return pd.DataFrame(columns=["Description", "Category", "normalized_entity"])
    frame = frame.drop_duplicates(subset=["normalized_entity", "confirmed_category"], keep="last")
    return frame.rename(columns={"transaction_description": "Description", "confirmed_category": "Category"})[["Description", "Category", "normalized_entity"]]


def combine_training_data(original_path=None, feedback_path=None):
    original_path = Path(original_path or config.TRAINING_DATA_PATH)
    original = pd.read_csv(original_path)
    label_column = "Final_Label" if "Final_Label" in original.columns else "Category"
    original = original[["Description", label_column]].rename(columns={label_column: "Category"})
    feedback = validated_feedback(feedback_path)
    combined = pd.concat([original, feedback[["Description", "Category"]]], ignore_index=True)
    combined = combined.drop_duplicates(subset=["Description", "Category"]).reset_index(drop=True)
    return original, feedback, combined


def retrain_from_feedback(*, original_path=None, feedback_path=None, candidate_path=None, minimum=None):
    minimum = int(minimum if minimum is not None else config.FEEDBACK_RETRAIN_MINIMUM)
    original, feedback, combined = combine_training_data(original_path, feedback_path)
    unique_entities = int(feedback["normalized_entity"].nunique()) if not feedback.empty else 0
    report = {
        "original_training_row_count": len(original),
        "feedback_row_count": len(feedback),
        "combined_training_row_count": len(combined),
        "unique_feedback_entities": unique_entities,
        "category_distribution": feedback["Category"].value_counts().to_dict() if not feedback.empty else {},
        "unknown_feedback_labels": int((feedback["Category"] == "Unknown").sum()) if not feedback.empty else 0,
        "p2p_feedback_labels": int((feedback["Category"] == "P2P").sum()) if not feedback.empty else 0,
        "duplicate_feedback_rows_removed": len(load_feedback(feedback_path)) - len(feedback),
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "minimum_feedback_entities": minimum,
        "status": "NOT_READY",
        "message": "Not enough new human feedback for batch retraining.",
    }
    if unique_entities < minimum:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2))
        return report

    with tempfile.NamedTemporaryFile("w", suffix=".csv", encoding="utf-8", delete=False) as handle:
        combined.to_csv(handle.name, index=False)
        combined_path = Path(handle.name)
    classifier = ExpenseClassifier(combined_path, use_entity_features=True)
    candidate = Path(candidate_path or config.PHASE4_CANDIDATE_MODEL_PATH)
    candidate.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(classifier, candidate)
    phase2_eval_path = Path(original_path or config.TRAINING_DATA_PATH)
    phase2_transaction = evaluate_seed_dataset(phase2_eval_path, use_entity_features=True)
    candidate_transaction = evaluate_seed_dataset(combined_path, use_entity_features=True)
    phase2_merchant = evaluate_unseen_merchants(phase2_eval_path, use_entity_features=True)
    candidate_merchant = evaluate_unseen_merchants(combined_path, use_entity_features=True)
    report.update({"status": "CANDIDATE_READY", "message": "Candidate trained; active Phase 2 model was not replaced.", "candidate_path": str(candidate)})
    recommendation = "CANDIDATE_IMPROVED" if candidate_merchant["weighted_f1"] > phase2_merchant["weighted_f1"] and candidate_transaction["weighted_f1"] >= phase2_transaction["weighted_f1"] else "CANDIDATE_NOT_IMPROVED"
    comparison = {
        "phase2": {"transaction_level": phase2_transaction, "unseen_merchant": phase2_merchant},
        "phase4_candidate": {"transaction_level": candidate_transaction, "unseen_merchant": candidate_merchant},
        "difference": {
            "transaction_accuracy": candidate_transaction["accuracy"] - phase2_transaction["accuracy"],
            "transaction_macro_f1": candidate_transaction["macro_f1"] - phase2_transaction["macro_f1"],
            "transaction_weighted_f1": candidate_transaction["weighted_f1"] - phase2_transaction["weighted_f1"],
            "merchant_accuracy": candidate_merchant["accuracy"] - phase2_merchant["accuracy"],
            "merchant_macro_f1": candidate_merchant["macro_f1"] - phase2_merchant["macro_f1"],
            "merchant_weighted_f1": candidate_merchant["weighted_f1"] - phase2_merchant["weighted_f1"],
        },
        "evaluation_split": "Existing transaction holdout and grouped unseen-merchant methodology; candidate remains inactive.",
        "recommendation": recommendation,
    }
    COMPARISON_PATH.parent.mkdir(parents=True, exist_ok=True)
    COMPARISON_PATH.write_text(json.dumps(comparison, indent=2, default=str))
    REPORT_PATH.write_text(json.dumps(report, indent=2, default=str))
    return report


if __name__ == "__main__":
    print(json.dumps(retrain_from_feedback(), indent=2, default=str))

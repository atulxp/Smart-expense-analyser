"""Generate Phase 1 evaluation artifacts from the supported PDF fixtures."""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import clean_data, extract_text_from_pdf, parse_transactions
from src.analytics.evaluation import (
    comparison_metrics,
    confidence_calibration,
    evaluate_seed_dataset,
    evaluate_unseen_merchants,
)
from src.nlp.categorizer import categorize_dataframe
from src.nlp.preprocessing import clean_text

REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)


def load_transactions():
    frames = []
    for filename in ("sample1.pdf", "sample2.pdf"):
        parsed = parse_transactions(extract_text_from_pdf(str(ROOT / filename)))
        frames.append(categorize_dataframe(clean_data(pd.DataFrame(parsed))))
    return pd.concat(frames, ignore_index=True)


def diagnostic_reason(row):
    if row["Final_Category"] == "P2P":
        return "Positive P2P evidence: " + str(row["P2P_Evidence"])
    if row["Final_Category"] == "Unknown":
        if row["Entity_Type"] == "PERSON":
            return "Person-like entity without explicit transfer evidence; abstained."
        if row["Category_Confidence"] < 0.60:
            return "No category reached the configured confidence threshold."
        return "No reliable category evidence remained after baseline protection."
    return "Assigned from baseline, NLP, or reviewed merchant/service evidence."


def write_non_misc_audit(frame):
    path = REPORTS / "non_misc_changes.csv"
    previous = pd.read_csv(path) if path.exists() else pd.DataFrame()
    previous_map = {}
    if not previous.empty and "Description" in previous:
        for _, row in previous.iterrows():
            previous_map.setdefault(row["Description"], row.to_dict())

    changed = frame[(frame["Baseline_Category"] != "Unknown") & (frame["Baseline_Category"] != frame["Final_Category"])].copy()
    rows = []
    for _, row in changed.iterrows():
        old = previous_map.get(row["Description"], {})
        rows.append({
            "Description": row["Description"],
            "Cleaned_Description": row["Preprocessed_Text"],
            "Merchant": row["Merchant"],
            "Entity_Type": row["Entity_Type"],
            "Baseline_Category": row["Baseline_Category"],
            "NLP_Category": row["NLP_Category"],
            "Category_Confidence": row["Category_Confidence"],
            "Final_Category": row["Final_Category"],
            "Categorization_Method": row["Categorization_Method"],
            "Assessment": old.get("Review", "AMBIGUOUS"),
            "Reason": old.get("Review_Rationale", "Requires manual evidence review."),
        })
    pd.DataFrame(rows).to_csv(path, index=False)


def write_p2p_unknown_diagnostic(frame):
    selected = frame[frame["Final_Category"].isin(["P2P", "Unknown"])].copy()
    rows = []
    for _, row in selected.iterrows():
        evidence = row["P2P_Evidence"] if isinstance(row["P2P_Evidence"], dict) else {}
        if row["Final_Category"] == "P2P":
            reason = "Positive transfer evidence is present."
            assessment = "LIKELY_P2P"
        elif row["Entity_Type"] == "PERSON" and not evidence.get("positive", False):
            reason = "PERSON detected, but no explicit transfer evidence."
            assessment = "PERSON_WITHOUT_P2P_EVIDENCE"
        elif row["Business_Indicators"]:
            reason = "Business/service indicators exist, but category evidence is insufficient."
            assessment = "UNKNOWN_WITH_BUSINESS_EVIDENCE"
        elif row["Category_Confidence"] < 0.60:
            reason = "Low-confidence prediction; abstained rather than forcing a category."
            assessment = "LOW_CONFIDENCE"
        else:
            reason = "Insufficient evidence to assign a legitimate category."
            assessment = "UNKNOWN_UNRESOLVED"
        rows.append({
            "Description": row["Description"],
            "Cleaned_Description": row["Preprocessed_Text"],
            "Merchant": row["Merchant"],
            "Entity_Type": row["Entity_Type"],
            "Baseline_Category": row["Baseline_Category"],
            "NLP_Category": row["NLP_Category"],
            "Category_Confidence": row["Category_Confidence"],
            "P2P_Evidence": json.dumps(evidence, sort_keys=True),
            "Final_Category": row["Final_Category"],
            "Categorization_Method": row["Categorization_Method"],
            "Assessment": assessment,
            "Reason": reason,
        })
    pd.DataFrame(rows).to_csv(REPORTS / "p2p_unknown_diagnostic.csv", index=False)


def write_comparison(frame):
    baseline_counts = frame["Baseline_Category"].replace({"P2P / Misc": "Unknown"}).value_counts()
    final_counts = frame["Final_Category"].value_counts()
    metrics = comparison_metrics(frame)
    rows = [{"Metric": "Total transactions", "Baseline": len(frame), "Enhanced": len(frame)}]
    rows.append({"Metric": "Baseline label note", "Baseline": "Legacy P2P / Misc", "Enhanced": "Canonical P2P / Unknown"})
    for category in ("P2P", "Unknown", "Food", "Travel", "Shopping", "Entertainment", "Health", "Utilities"):
        rows.append({"Metric": category, "Baseline": int(baseline_counts.get(category, 0)), "Enhanced": int(final_counts.get(category, 0))})
    for metric, value in {
        "ML classifications": metrics["ml_transactions"],
        "Keyword classifications": metrics["keyword_transactions"],
        "Entity classifications": int((frame["Categorization_Method"] == "P2P_EVIDENCE").sum()),
        "Web classifications": metrics["web_transactions"],
        "Fallback classifications": int((frame["Categorization_Method"] == "ABSTAIN").sum()),
    }.items():
        rows.append({"Metric": metric, "Baseline": "", "Enhanced": value})
    pd.DataFrame(rows).to_csv(REPORTS / "final_comparison.csv", index=False)


def main():
    frame = load_transactions()
    write_non_misc_audit(frame)
    write_p2p_unknown_diagnostic(frame)
    write_comparison(frame)
    evaluation_data = ROOT / "data" / "real_transaction_samples.csv"
    if not evaluation_data.exists():
        evaluation_data = ROOT / "data" / "training_transactions.csv"
        print("Real transaction labels are omitted from the public repository; using synthetic training data.")
    transaction_metrics = evaluate_seed_dataset(evaluation_data)
    merchant_metrics = evaluate_unseen_merchants(evaluation_data)
    evaluation = {
        "transaction_level": transaction_metrics,
        "merchant_level": merchant_metrics,
        "confidence_bands": confidence_calibration(evaluation_data),
        "full_dataset": comparison_metrics(frame),
        "class_distribution": {
            "baseline": frame["Baseline_Category"].replace({"P2P / Misc": "Unknown"}).value_counts().to_dict(),
            "enhanced": frame["Final_Category"].value_counts().to_dict(),
        },
    }
    (REPORTS / "model_evaluation.json").write_text(json.dumps(evaluation, indent=2, default=str))
    print(json.dumps({"transactions": len(frame), "full_dataset": evaluation["full_dataset"], "transaction_level": {key: transaction_metrics.get(key) for key in ("accuracy", "macro_f1", "weighted_f1")}, "merchant_level": {key: merchant_metrics.get(key) for key in ("accuracy", "macro_f1", "weighted_f1")}}, indent=2))


if __name__ == "__main__":
    main()

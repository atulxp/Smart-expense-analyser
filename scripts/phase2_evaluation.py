"""Phase 2 before/after evaluation for entity and business feature tokens."""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import clean_data, extract_text_from_pdf, parse_transactions
from src.analytics.evaluation import evaluate_seed_dataset, evaluate_unseen_merchants
from src.nlp.categorizer import categorize_dataframe, _canonical_category, _explicit_categories, get_classifier
from src.nlp.classifier import ExpenseClassifier
from src.nlp.entity_extraction import extract_entities
from src.nlp.preprocessing import preprocess_description
import config

REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)


def load_transactions():
    frames = []
    for filename in ("sample1.pdf", "sample2.pdf"):
        parsed = parse_transactions(extract_text_from_pdf(str(ROOT / filename)))
        frames.append(clean_data(pd.DataFrame(parsed)))
    return pd.concat(frames, ignore_index=True)


def before_result(description, classifier):
    baseline = _canonical_category(config.get_category(description))
    entities = extract_entities(description)
    prediction = classifier.predict(description)
    category = _canonical_category(prediction["category"])
    final = baseline
    method = "KEYWORD" if baseline != "Unknown" else "ABSTAIN"
    if prediction["confidence"] >= config.ML_CONFIDENCE_THRESHOLD:
        explicit = _explicit_categories(description)
        if baseline == "Unknown" or category == baseline or category in explicit:
            final = category if category not in {"P2P", "P2P / Misc"} else "Unknown"
            method = "ML"
    return {
        "Final_Category": final,
        "NLP_Category": category,
        "Category_Confidence": prediction["confidence"],
        "Categorization_Method": method,
        "Entity_Type": entities["entity_type"],
        "Merchant": entities["merchant"],
    }


def confidence_bands(values):
    bands = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]
    return {f"{low:.1f}-{min(high, 1.0):.1f}": int(((values >= low) & (values < high)).sum()) for low, high in bands}


def main():
    raw = load_transactions()
    before_classifier = ExpenseClassifier(config.TRAINING_DATA_PATH, use_entity_features=False)
    before = pd.DataFrame([before_result(value, before_classifier) for value in raw["Description"]])
    after = categorize_dataframe(raw)
    combined = pd.DataFrame({
        "transaction_description": raw["Description"],
        "entity_type": after["Entity_Type"],
        "before_category": before["Final_Category"],
        "after_category": after["Final_Category"],
        "before_confidence": before["Category_Confidence"],
        "after_confidence": after["Category_Confidence"],
        "before_method": before["Categorization_Method"],
        "after_method": after["Categorization_Method"],
        "merchant": after["Merchant"],
        "business_indicators": after["Business_Indicators"],
        "entity_feature_tokens": raw["Description"].map(lambda value: " ".join(__import__("src.nlp.entity_extraction", fromlist=["entity_feature_tokens"]).entity_feature_tokens(value))),
    })
    changes = combined[combined["before_category"] != combined["after_category"]].copy()
    changes["reason_features"] = changes.apply(lambda row: f"entity={row['entity_type']}; indicators={row['business_indicators']}; tokens={row['entity_feature_tokens']}", axis=1)
    changes.to_csv(REPORTS / "phase2_category_changes.csv", index=False)

    known_cases = [
        "shawarmatown", "OhoShawarmaPanvel", "BundlTechnologiespvtLtd", "TIWARIENTERPRISE",
        "GARUDENTERPRISES", "KanhaCaterers", "GUPTASANDWICHANDSNACKS", "MumbaiMetro",
        "IndianRailwayTicketing", "YouTube", "Airtel", "Rapido", "UrbanMart", "XYZ MART INVOICE 8821",
        "AMZN INDIA ORDER", "UPI-SWIGGY-93821", "SWIGGY TECHNOLOGIES MUMBAI", "UBER TRIP 87432", "APOLLO PHARMACY POS",
    ]
    case_rows = []
    for description in known_cases:
        row = after[after["Description"] == description]
        if row.empty:
            result = categorize_dataframe(pd.DataFrame({"Description": [description]})).iloc[0]
        else:
            result = row.iloc[0]
        case_rows.append({
            "Description": description,
            "Entity_Type": result["Entity_Type"],
            "Merchant": result["Merchant"],
            "Final_Category": result["Final_Category"],
            "NLP_Category": result["NLP_Category"],
            "Confidence": result["Category_Confidence"],
            "Business_Indicators": result["Business_Indicators"],
        })
    pd.DataFrame(case_rows).to_csv(REPORTS / "phase2_known_cases.csv", index=False)

    evaluation_data = ROOT / "data" / "real_transaction_samples.csv"
    if not evaluation_data.exists():
        evaluation_data = ROOT / "data" / "training_transactions.csv"
    before_transaction = evaluate_seed_dataset(evaluation_data, use_entity_features=False)
    after_transaction = evaluate_seed_dataset(evaluation_data, use_entity_features=True)
    before_merchant = evaluate_unseen_merchants(evaluation_data, use_entity_features=False)
    after_merchant = evaluate_unseen_merchants(evaluation_data, use_entity_features=True)
    report = {
        "dataset_transactions": len(raw),
        "before": {
            "transaction_level": before_transaction,
            "unseen_merchant": before_merchant,
            "confidence_bands": confidence_bands(before["Category_Confidence"]),
        },
        "after": {
            "transaction_level": after_transaction,
            "unseen_merchant": after_merchant,
            "confidence_bands": confidence_bands(after["Category_Confidence"]),
        },
        "category_changes": {
            "count": len(changes),
            "entity_type_distribution": changes["entity_type"].value_counts().to_dict(),
            "before_after": pd.crosstab(changes["before_category"], changes["after_category"]).to_dict(),
        },
        "unknown_counts": {
            "before": int((before["Final_Category"] == "Unknown").sum()),
            "after": int((after["Final_Category"] == "Unknown").sum()),
        },
        "person_counts": {
            "before": int((before["Entity_Type"] == "PERSON").sum()),
            "after": int((after["Entity_Type"] == "PERSON").sum()),
        },
        "feature_policy": "Entity type and explainable business/payment indicators are appended as tokens to the existing word+character TF-IDF matrix. Model family and confidence threshold are unchanged.",
        "phase1_reference": {
            "transaction_level": {"accuracy": 0.8181818181818182, "macro_f1": 0.622549019607843, "weighted_f1": 0.7761437908496733},
            "unseen_merchant": {"accuracy": 0.6060606060606061, "macro_f1": 0.46820987654320984, "weighted_f1": 0.5431537598204265},
            "note": "Historical Phase 1 report values. Phase 2 entity normalization can change merchant grouping; the after score is evaluated with the current normalized grouping.",
        },
    }
    (REPORTS / "phase2_evaluation.json").write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps({
        "transactions": len(raw),
        "category_changes": len(changes),
        "unknown_before_after": report["unknown_counts"],
        "transaction_metrics": {key: {metric: value for metric, value in result.items() if metric in {"accuracy", "macro_f1", "weighted_f1"}} for key, result in {"before": before_transaction, "after": after_transaction}.items()},
        "merchant_metrics": {key: {metric: value for metric, value in result.items() if metric in {"accuracy", "macro_f1", "weighted_f1"}} for key, result in {"before": before_merchant, "after": after_merchant}.items()},
    }, indent=2))


if __name__ == "__main__":
    main()

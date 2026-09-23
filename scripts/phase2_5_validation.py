"""Diagnostic-only post-Phase-2 validation. Does not change application behavior."""

import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config
from app import clean_data, extract_text_from_pdf, parse_transactions
from src.nlp.categorizer import categorize_dataframe
from src.nlp.classifier import model_text
from src.analytics.evaluation import canonical_label

REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)


def load_full_dataset():
    config.WEB_ENRICHMENT_ENABLED = False
    frames = []
    for filename in ("sample1.pdf", "sample2.pdf"):
        parsed = parse_transactions(extract_text_from_pdf(str(ROOT / filename)))
        frames.append(categorize_dataframe(clean_data(pd.DataFrame(parsed))))
    return pd.concat(frames, ignore_index=True)


def movement_assessment(row):
    description = str(row["transaction_description"]).lower()
    indicators = str(row["business_indicators"]).lower()
    before = row["before_category"]
    after = row["after_category"]
    if before == "Unknown" and after == "Food":
        if any(term in description or term in indicators for term in ("catering", "sweets", "snacks", "shawarma", "hotel", "sandwich")):
            return "PLAUSIBLE", "Food-service wording supports the Food category."
        if any(term in description for term in ("retail", "advisory", "technology", "enterprise", "limited", "company")):
            return "SUSPICIOUS", "Business wording does not provide specific Food evidence."
        return "AMBIGUOUS", "The description has insufficient category-specific evidence."
    if before == "Unknown" and after == "Travel":
        if "auto service" in description or "service" in indicators:
            return "PLAUSIBLE", "Auto-service wording supports a transport-related expense."
        return "AMBIGUOUS", "Travel evidence is indirect and requires transaction context."
    if before != "Unknown" and after == "Unknown":
        if row["entity_type"] == "PERSON" and not indicators:
            return "PLAUSIBLE", "The feature model abstained on a person-like string without business evidence."
        return "AMBIGUOUS", "Abstention may be reasonable, but available text is insufficient to verify the prior category."
    return "", ""


def write_movement_audit(changes):
    rows = []
    for _, row in changes.iterrows():
        assessment, reason = movement_assessment(row)
        rows.append({
            "transaction_description": row["transaction_description"],
            "entity_type": row["entity_type"],
            "merchant": row["merchant"],
            "before_category": row["before_category"],
            "after_category": row["after_category"],
            "before_confidence": row["before_confidence"],
            "after_confidence": row["after_confidence"],
            "categorization_method": row["after_method"],
            "business_indicators": row["business_indicators"],
            "audit_assessment": assessment,
            "audit_reason": reason,
        })
    audit = pd.DataFrame(rows)
    audit.to_csv(REPORTS / "phase2_movement_audit.csv", index=False)
    return audit


def confidence_summary(frame):
    bands = {
        ">=0.8": frame["Category_Confidence"] >= 0.8,
        ">=0.9": frame["Category_Confidence"] >= 0.9,
        "0.6-0.8": (frame["Category_Confidence"] >= 0.6) & (frame["Category_Confidence"] < 0.8),
        "<0.6": frame["Category_Confidence"] < 0.6,
    }
    rows = []
    for category in ("Food", "Shopping", "Travel", "Entertainment", "Health", "Utilities", "Unknown", "P2P"):
        subset = frame[frame["Final_Category"] == category]
        row = {"final_category": category, "total": len(subset)}
        row.update({name: int(mask.loc[subset.index].sum()) for name, mask in bands.items()})
        rows.append(row)
    return pd.DataFrame(rows)


def reviewed_holdout_confidence_bands():
    path = ROOT / "data" / "real_transaction_samples.csv"
    if not path.exists():
        return {"status": "No private reviewed real-data labels available in this checkout."}
    data = pd.read_csv(path).dropna(subset=["Description", "Final_Label"])
    data["Label"] = data["Final_Label"].map(canonical_label)
    train, validation = train_test_split(data, test_size=0.20, random_state=42, stratify=data["Label"])
    vectorizer = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True)),
    ])
    model = LogisticRegression(C=10.0, max_iter=1000, random_state=42)
    model.fit(vectorizer.fit_transform(train["Description"].map(model_text)), train["Label"])
    probabilities = model.predict_proba(vectorizer.transform(validation["Description"].map(model_text)))
    predicted = model.classes_[probabilities.argmax(axis=1)]
    confidence = probabilities.max(axis=1)
    rows = []
    for lower, upper in ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)):
        mask = (confidence >= lower) & (confidence < upper)
        rows.append({
            "band": f"{lower:.1f}-{min(upper, 1.0):.1f}",
            "count": int(mask.sum()),
            "accuracy": float(accuracy_score(validation.loc[mask, "Label"], predicted[mask])) if mask.any() else None,
        })
    return {"status": "Reviewed 20% holdout", "bands": rows}


def unknown_summary(frame):
    unknown = frame[frame["Final_Category"] == "Unknown"].copy()
    unknown["normalized_entity"] = unknown["Merchant"].where(unknown["Merchant"] != "Unknown", unknown["Description"])
    grouped = unknown.groupby(["normalized_entity", "Entity_Type"], dropna=False).agg(
        transaction_count=("Description", "size"),
        average_confidence=("Category_Confidence", "mean"),
        representative_descriptions=("Description", lambda values: " | ".join(dict.fromkeys(values).keys())),
    ).reset_index().sort_values(["transaction_count", "normalized_entity"], ascending=[False, True]).head(20)
    return grouped


def known_cases(frame):
    cases = [
        "shawarmatown", "OhoShawarmaPanvel", "BundlTechnologiespvtLtd", "TIWARIENTERPRISE",
        "GARUDENTERPRISES", "KanhaCaterers", "GUPTASANDWICHANDSNACKS", "MumbaiMetro",
        "IndianRailwayTicketing", "YouTube", "Airtel", "Rapido", "UrbanMart", "XYZ MART INVOICE 8821",
        "AMZN INDIA ORDER", "UPI-SWIGGY-93821", "SWIGGY TECHNOLOGIES MUMBAI", "UBER TRIP 87432", "APOLLO PHARMACY POS",
    ]
    rows = []
    for description in cases:
        result = categorize_dataframe(pd.DataFrame({"Description": [description]})).iloc[0]
        rows.append({
            "Description": description,
            "Entity": result["Entity_Type"],
            "Final_Category": result["Final_Category"],
            "Confidence": result["Category_Confidence"],
            "Method": result["Categorization_Method"],
        })
    return pd.DataFrame(rows)


def main():
    frame = load_full_dataset()
    changes = pd.read_csv(REPORTS / "phase2_category_changes.csv")
    movement_audit = write_movement_audit(changes)
    confidence = confidence_summary(frame)
    unknown = unknown_summary(frame)
    cases = known_cases(frame)
    confidence.to_csv(REPORTS / "phase2_confidence_by_category.csv", index=False)
    unknown.to_csv(REPORTS / "phase2_unknown_top20.csv", index=False)
    cases.to_csv(REPORTS / "phase2_known_cases_audit.csv", index=False)

    movement_groups = changes.assign(
        movement_type=changes.apply(lambda row: "Unknown -> Category" if row["before_category"] == "Unknown" and row["after_category"] != "Unknown" else "Category -> Unknown" if row["after_category"] == "Unknown" else "Other", axis=1)
    )
    entity_breakdown = pd.crosstab(movement_groups["entity_type"], movement_groups["movement_type"]).to_dict()
    summary = {
        "transactions": len(frame),
        "category_movements": len(changes),
        "movement_assessments": movement_audit["audit_assessment"].value_counts().to_dict(),
        "unknown_to_category": changes[(changes["before_category"] == "Unknown") & (changes["after_category"] != "Unknown")]["after_category"].value_counts().to_dict(),
        "category_to_unknown": changes[changes["after_category"] == "Unknown"]["before_category"].value_counts().to_dict(),
        "movement_by_entity_and_type": entity_breakdown,
        "confidence_overview": {
            "at_least_0_8": int((frame["Category_Confidence"] >= 0.8).sum()),
            "at_least_0_9": int((frame["Category_Confidence"] >= 0.9).sum()),
            "0_6_to_0_8": int(((frame["Category_Confidence"] >= 0.6) & (frame["Category_Confidence"] < 0.8)).sum()),
            "below_0_6": int((frame["Category_Confidence"] < 0.6).sum()),
        },
        "unknown_by_entity_type": frame[frame["Final_Category"] == "Unknown"]["Entity_Type"].value_counts().to_dict(),
        "full_integrity": {
            "row_count": len(frame),
            "description_duplicates": int(frame["Description"].duplicated().sum()),
            "nan_final_categories": int(frame["Final_Category"].isna().sum()),
            "invalid_categories": sorted(set(frame["Final_Category"]) - {"Food", "Shopping", "Travel", "Entertainment", "Health", "Utilities", "P2P", "Unknown"}),
            "p2p_count": int((frame["Final_Category"] == "P2P").sum()),
        },
        "ground_truth_limit": "Full 923-transaction confidence correctness cannot be measured because the full dataset has no independent ground-truth labels. Confidence-band accuracy is available only for the reviewed holdout in reports/phase2_evaluation.json.",
        "reviewed_holdout_confidence_bands": reviewed_holdout_confidence_bands(),
    }
    (REPORTS / "phase2_5_validation_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    print("PHASE 2.5 VALIDATION")
    print(json.dumps(summary, indent=2, default=str))
    print("\nCONFIDENCE BY FINAL CATEGORY")
    print(confidence.to_string(index=False))
    print("\nTOP UNKNOWN ENTITIES")
    print(unknown.to_string(index=False))
    print("\nKNOWN CASES")
    print(cases.to_string(index=False))


if __name__ == "__main__":
    main()

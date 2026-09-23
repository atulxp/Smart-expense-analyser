"""Read-only PERSON entity audit for the supported PDF fixtures."""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import clean_data, extract_text_from_pdf, parse_transactions
from src.nlp.categorizer import categorize_dataframe
from src.nlp.preprocessing import clean_text

REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)


def load_transactions() -> pd.DataFrame:
    frames = []
    for filename in ("sample1.pdf", "sample2.pdf"):
        parsed = parse_transactions(extract_text_from_pdf(str(ROOT / filename)))
        frames.append(categorize_dataframe(clean_data(pd.DataFrame(parsed))))
    return pd.concat(frames, ignore_index=True)


def confidence_band(value: float) -> str:
    for lower, upper in ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)):
        if lower <= value < upper:
            return f"{lower:.1f}-{min(upper, 1.0):.1f}"
    return "unknown"


def select_representative_sample(person: pd.DataFrame, size: int = 100) -> pd.DataFrame:
    unique = person.drop_duplicates(subset=["Description"]).copy()
    frequencies = person["Description"].value_counts().rename("Description_Frequency")
    if "Description_Frequency" not in unique.columns:
        unique = unique.join(frequencies, on="Description")
    unique["Confidence_Band"] = unique["Category_Confidence"].map(confidence_band)
    unique["Outcome_Group"] = unique["Final_Category"].where(unique["Final_Category"].isin(["P2P", "Unknown"]), "LEGITIMATE_CATEGORY")
    unique["Entity_Group"] = unique["Merchant"].where(unique["Merchant"] != "Unknown", unique["Description"])

    # First cover entity groups, then fill quota across confidence and outcome strata.
    representatives = unique.sort_values(["Description_Frequency", "Entity_Group"], ascending=[False, True]).groupby("Entity_Group", as_index=False).head(1)
    if len(representatives) > size:
        representatives = representatives.sample(size, random_state=42)
    remaining = unique.drop(index=representatives.index)
    needed = size - len(representatives)
    if needed > 0 and not remaining.empty:
        strata = remaining.groupby(["Confidence_Band", "Outcome_Group"], group_keys=False)
        extras = strata.apply(lambda group: group.sample(min(len(group), max(1, needed // max(1, len(strata)))), random_state=42), include_groups=False)
        extras = remaining.loc[extras.index] if len(extras) else remaining.iloc[0:0]
        if len(extras) < needed:
            extras = pd.concat([extras, remaining.drop(index=extras.index).sample(min(needed - len(extras), len(remaining) - len(extras)), random_state=42)])
        representatives = pd.concat([representatives, extras]).drop_duplicates(subset=["Description"]).head(size)
    return representatives.sort_values(["Entity_Group", "Description"]).reset_index(drop=True)


def main() -> None:
    frame = load_transactions()
    person = frame[frame["Entity_Type"] == "PERSON"].copy()
    person["Description_Frequency"] = person["Description"].map(person["Description"].value_counts())
    person["Confidence_Band"] = person["Category_Confidence"].map(confidence_band)
    person["Normalized_Entity"] = person["Merchant"].where(person["Merchant"] != "Unknown", person["Description"])
    potential_indicators = (
        "store", "stores", "shop", "mart", "market", "enterprise", "enterprises", "ltd",
        "pharmacy", "clinic", "hospital", "restaurant", "cafe", "bakery", "dairy", "traders",
        "services", "solutions", "shawarma", "railway", "metro", "ticket", "wallet", "caterers",
        "foods", "snacks", "panshop", "medical", "autoservice", "transport", "youtube", "ajio",
    )
    potential_business_rows = person[person["Description"].str.lower().str.contains("|".join(potential_indicators), regex=True, na=False)]
    cleaned_groups = person.groupby("Preprocessed_Text")["Description"].agg(lambda values: sorted(set(values)))
    surface_form_groups = {key: values for key, values in cleaned_groups.items() if len(values) > 1}

    audit_columns = {
        "Description": "transaction_description",
        "Preprocessed_Text": "cleaned_description",
        "Normalized_Entity": "normalized_merchant_or_entity",
        "Entity_Type": "entity_type",
        "Baseline_Category": "baseline_category",
        "NLP_Category": "nlp_category",
        "Category_Confidence": "nlp_confidence",
        "Final_Category": "final_category",
        "Categorization_Method": "categorization_method",
        "P2P_Evidence": "p2p_evidence",
        "Business_Indicators": "merchant_service_indicators",
        "Description_Frequency": "description_frequency",
        "Confidence_Band": "confidence_band",
    }
    full_audit = person[list(audit_columns)].rename(columns=audit_columns)
    full_audit["p2p_evidence"] = full_audit["p2p_evidence"].map(lambda value: json.dumps(value, sort_keys=True, default=str))
    full_audit.to_csv(REPORTS / "person_entity_audit.csv", index=False)

    sample = select_representative_sample(person)
    review = sample[list(audit_columns)].rename(columns=audit_columns)
    review["audit_label"] = ""
    review["audit_reason"] = ""
    review["p2p_evidence"] = review["p2p_evidence"].map(lambda value: json.dumps(value, sort_keys=True, default=str))
    review.to_csv(REPORTS / "person_entity_manual_review.csv", index=False)

    group = frame.copy()
    group["Entity_Group"] = group["Entity_Type"].replace({"MERCHANT": "MERCHANT/SERVICE", "SERVICE": "MERCHANT/SERVICE"})
    summary = {}
    for entity_group, rows in group.groupby("Entity_Group"):
        summary[entity_group] = {
            "count": int(len(rows)),
            "percentage": float(len(rows) / len(group) * 100),
            "average_ml_confidence": float(rows["Category_Confidence"].mean()),
            "final_category_distribution": rows["Final_Category"].value_counts().to_dict(),
            "baseline_category_distribution": rows["Baseline_Category"].value_counts().to_dict(),
        }

    person_entities = person["Description"].value_counts()
    repeated = person_entities[person_entities > 1]
    stats = {
        "total_transactions": len(frame),
        "person_transactions": len(person),
        "person_percentage": len(person) / len(frame) * 100,
        "unique_person_descriptions": int(person["Description"].nunique()),
        "repeated_person_descriptions": int((person_entities > 1).sum()),
        "average_transactions_per_unique_person_description": float(person_entities.mean()),
        "representative_sample_size": len(review),
        "sample_selection": "Deduplicated descriptions; one representative per normalized entity group where possible; remaining rows filled with deterministic stratification across confidence bands and final-outcome groups.",
        "confidence_distribution": person["Confidence_Band"].value_counts().sort_index().to_dict(),
        "most_common_person_descriptions": person_entities.head(25).to_dict(),
        "most_common_repeated_person_descriptions": repeated.head(25).to_dict(),
        "person_final_category_distribution": person["Final_Category"].value_counts().to_dict(),
        "person_method_distribution": person["Categorization_Method"].value_counts().to_dict(),
        "potential_business_or_service_indicator_rows": int(len(potential_business_rows)),
        "potential_business_or_service_indicator_examples": potential_business_rows["Description"].value_counts().head(30).to_dict(),
        "cleaned_text_groups_with_multiple_surface_forms": surface_form_groups,
        "entity_group_comparison": summary,
        "manual_audit_status": "UNLABELED: audit_label and audit_reason are intentionally blank for human review.",
    }
    (REPORTS / "person_entity_audit_summary.json").write_text(json.dumps(stats, indent=2, default=str))

    print("PERSON ENTITY AUDIT")
    print(f"Total transactions: {len(frame)}")
    print(f"PERSON transactions: {len(person)} ({len(person) / len(frame):.1%})")
    print(f"Unique PERSON descriptions: {person['Description'].nunique()}")
    print(f"Repeated PERSON descriptions: {(person_entities > 1).sum()}")
    print(f"Representative sample: {len(review)}")
    print("Confidence distribution:", stats["confidence_distribution"])
    print("\nEntity groups:")
    for key, value in summary.items():
        print(key, value["count"], f"({value['percentage']:.1f}%)", value["final_category_distribution"])
    print("\nRepresentative preview grouped by normalized entity:")
    preview = review[["transaction_description", "normalized_merchant_or_entity", "baseline_category", "nlp_category", "nlp_confidence", "final_category"]]
    for entity, rows in preview.groupby("normalized_merchant_or_entity", sort=True):
        print(f"\nPERSON ENTITY: {entity}")
        print(rows.head(5).to_string(index=False))


if __name__ == "__main__":
    main()

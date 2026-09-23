"""Review queue generation for unresolved recurring entities."""

from pathlib import Path

import pandas as pd

import config
from .merchant_memory import get_memory_category, normalize_entity_key


def build_review_queue(frame: pd.DataFrame, limit: int = 25, path: Path | None = None) -> pd.DataFrame:
    unresolved = frame[frame["Final_Category"] == "Unknown"].copy()
    if unresolved.empty:
        queue = pd.DataFrame(columns=["normalized_entity", "entity_type", "transaction_count", "average_confidence", "representative_description", "current_category", "review_status"])
    else:
        unresolved["normalized_entity"] = unresolved.apply(
            lambda row: normalize_entity_key(row["Description"], row.get("Merchant")), axis=1
        )
        queue = unresolved.groupby(["normalized_entity", "Entity_Type"], as_index=False).agg(
            transaction_count=("Description", "size"),
            average_confidence=("Category_Confidence", "mean"),
            representative_description=("Description", lambda values: " | ".join(dict.fromkeys(values).keys())[:500]),
        )
        queue = queue.rename(columns={"Entity_Type": "entity_type"})
        queue["current_category"] = "Unknown"
        queue["review_status"] = queue["normalized_entity"].map(
            lambda entity: "CONFIRMED" if get_memory_category(entity) is not None else "PENDING"
        )
        queue = queue.sort_values(["review_status", "transaction_count", "normalized_entity"], ascending=[True, False, True]).head(limit).reset_index(drop=True)
    output = Path(path or config.MERCHANT_REVIEW_QUEUE_PATH)
    output.parent.mkdir(parents=True, exist_ok=True)
    queue.to_csv(output, index=False)
    return queue

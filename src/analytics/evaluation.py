"""Dataset-grounded baseline versus enhanced metrics."""

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import FeatureUnion

from src.nlp.preprocessing import clean_text
from src.nlp.entity_extraction import extract_entities


def canonical_label(label: str) -> str:
    return "Unknown" if label in {"P2P / Misc", "Others", ""} else label


def _build_vectorizer() -> FeatureUnion:
    return FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True)),
    ])


def _metric_report(actual, predicted, labels=None) -> dict:
    from sklearn.metrics import classification_report, confusion_matrix
    labels = labels or sorted(set(actual) | set(predicted))
    report = classification_report(actual, predicted, labels=labels, output_dict=True, zero_division=0)
    return {
        "accuracy": accuracy_score(actual, predicted),
        "precision": precision_score(actual, predicted, average="weighted", zero_division=0),
        "recall": recall_score(actual, predicted, average="weighted", zero_division=0),
        "weighted_f1": f1_score(actual, predicted, average="weighted", zero_division=0),
        "macro_f1": f1_score(actual, predicted, average="macro", zero_division=0),
        "labels": labels,
        "per_class": {label: report.get(label, {}) for label in labels},
        "confusion_matrix": confusion_matrix(actual, predicted, labels=labels).tolist(),
        "sample_size": len(actual),
    }


def comparison_metrics(df: pd.DataFrame) -> dict:
    total = len(df)
    baseline_misc = int((df["Baseline_Category"].isin(["P2P / Misc", "Unknown"])).sum()) if total else 0
    final_misc = int((df["Final_Category"].isin(["P2P / Misc", "Unknown"])).sum()) if total else 0
    return {
        "total_transactions": total,
        "keyword_transactions": int((df["Categorization_Method"] == "KEYWORD").sum()) if total else 0,
        "ml_transactions": int((df["Categorization_Method"] == "ML").sum()) if total else 0,
        "web_transactions": int((df["Web_Enriched"] == True).sum()) if total else 0,
        "unknown_merchants": int((df["Merchant"] == "Unknown").sum()) if total else 0,
        "person_entities": int((df["Transaction_Entity_Type"] == "PERSON").sum()) if total and "Transaction_Entity_Type" in df else 0,
        "merchant_entities": int(df["Transaction_Entity_Type"].isin(["MERCHANT", "SERVICE"]).sum()) if total and "Transaction_Entity_Type" in df else 0,
        "unknown_entities": int((df["Transaction_Entity_Type"] == "UNKNOWN").sum()) if total and "Transaction_Entity_Type" in df else 0,
        "baseline_unknown_count": baseline_misc,
        "final_unknown_count": final_misc,
        "baseline_p2p_count": int((df["Final_Category"] == "P2P").sum()) if total else 0,
        "final_p2p_count": int((df["Final_Category"] == "P2P").sum()) if total else 0,
        "baseline_misc_rate": baseline_misc / total if total else 0.0,
        "final_misc_rate": final_misc / total if total else 0.0,
    }


def evaluate_seed_dataset(path) -> dict:
    """Evaluate the seed data with a stratified holdout, when its size permits."""
    data = pd.read_csv(path)
    label_column = "Final_Label" if "Final_Label" in data.columns else "Category"
    data = data.dropna(subset=["Description", label_column])
    if len(data) < 12 or data[label_column].value_counts().min() < 2:
        return {"warning": "Seed dataset is too small for a reliable holdout evaluation.", "sample_size": len(data)}
    data[label_column] = data[label_column].map(canonical_label)
    train, test = train_test_split(data, test_size=0.20, random_state=42, stratify=data[label_column])
    vectorizer = _build_vectorizer()
    features = vectorizer.fit_transform(train["Description"].map(clean_text))
    model = LogisticRegression(C=10.0, max_iter=1000, random_state=42).fit(features, train[label_column])
    predicted = model.predict(vectorizer.transform(test["Description"].map(clean_text)))
    metrics = _metric_report(test[label_column].tolist(), predicted.tolist())
    return {
        "warning": "Holdout is based on manually reviewed real transaction samples; it is not a production accuracy estimate.",
        "sample_size": len(test),
        "accuracy": metrics["accuracy"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": f1_score(test[label_column], predicted, average="weighted", zero_division=0),
        "weighted_f1": metrics["weighted_f1"],
        "macro_f1": metrics["macro_f1"],
        "per_class": metrics["per_class"],
        "confusion_matrix": metrics["confusion_matrix"],
        "labels": metrics["labels"],
        "test_descriptions": test["Description"].tolist(),
        "test_labels": test[label_column].tolist(),
        "test_predictions": predicted.tolist(),
    }


def evaluate_unseen_merchants(path) -> dict:
    """Evaluate with normalized merchant groups kept wholly in train or test."""
    data = pd.read_csv(path).dropna(subset=["Description", "Final_Label"])
    data["Label"] = data["Final_Label"].map(canonical_label)
    data["Merchant_Group"] = data["Description"].map(
        lambda value: extract_entities(value)["merchant"] if extract_entities(value)["merchant"] != "Unknown" else clean_text(value)
    )
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=42)
    train_index, test_index = next(splitter.split(data, data["Label"], groups=data["Merchant_Group"]))
    train, test = data.iloc[train_index], data.iloc[test_index]
    vectorizer = _build_vectorizer()
    features = vectorizer.fit_transform(train["Description"].map(clean_text))
    model = LogisticRegression(C=10.0, max_iter=1000, random_state=42).fit(features, train["Label"])
    predicted = model.predict(vectorizer.transform(test["Description"].map(clean_text)))
    metrics = _metric_report(test["Label"].tolist(), predicted.tolist())
    return {
        "evaluation": "MERCHANT-LEVEL / UNSEEN-MERCHANT EVALUATION",
        "train_size": len(train), "test_size": len(test),
        "unseen_groups": int(test["Merchant_Group"].nunique()), **metrics,
    }


def confidence_calibration(path) -> dict:
    """Report validation accuracy by confidence band without changing thresholds."""
    data = pd.read_csv(path).dropna(subset=["Description", "Final_Label"])
    data["Label"] = data["Final_Label"].map(canonical_label)
    train, validation = train_test_split(data, test_size=0.20, random_state=42, stratify=data["Label"])
    vectorizer = _build_vectorizer()
    model = LogisticRegression(C=10.0, max_iter=1000, random_state=42).fit(
        vectorizer.fit_transform(train["Description"].map(clean_text)), train["Label"]
    )
    probabilities = model.predict_proba(vectorizer.transform(validation["Description"].map(clean_text)))
    predicted = model.classes_[probabilities.argmax(axis=1)]
    confidence = probabilities.max(axis=1)
    bands = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]
    return {
        f"{lower:.1f}-{min(upper, 1.0):.1f}": {
            "count": int(((confidence >= lower) & (confidence < upper)).sum()),
            "accuracy": float(accuracy_score(validation["Label"][(confidence >= lower) & (confidence < upper)], predicted[(confidence >= lower) & (confidence < upper)])) if ((confidence >= lower) & (confidence < upper)).any() else None,
        }
        for lower, upper in bands
    }

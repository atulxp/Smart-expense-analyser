"""Reusable TF-IDF and logistic-regression expense classifier."""

import logging
from pathlib import Path
from typing import Dict, Iterable, Optional

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion

from .preprocessing import clean_text
from .entity_extraction import entity_feature_tokens

LOGGER = logging.getLogger(__name__)


def _canonical_label(label: str) -> str:
    return "Unknown" if label in {"P2P / Misc", "Others", ""} else label


def model_text(description: str, use_entity_features: bool = True) -> str:
    text = clean_text(description)
    if not use_entity_features:
        return text
    return " ".join([text, *entity_feature_tokens(description)])


class ExpenseClassifier:
    def __init__(self, training_data_path: Path, use_entity_features: bool = True):
        self.training_data_path = Path(training_data_path)
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.model: Optional[LogisticRegression] = None
        self.training_size = 0
        self.use_entity_features = use_entity_features
        self._fit()

    def _fit(self) -> None:
        data = pd.read_csv(self.training_data_path)
        label_column = "Final_Label" if "Final_Label" in data.columns else "Category"
        data = data.dropna(subset=["Description", label_column])
        data = data[data[label_column].astype(str).str.strip() != ""]
        texts = [self._model_text(value) for value in data["Description"]]
        if len(data) < 2 or len(set(data[label_column])) < 2 or not any(texts):
            raise ValueError("Training data must contain at least two usable categories")
        self.vectorizer = FeatureUnion([
            ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True)),
        ])
        features = self.vectorizer.fit_transform(texts)
        self.model = LogisticRegression(C=10.0, max_iter=1000, random_state=42)
        self.model.fit(features, data[label_column].map(_canonical_label))
        self.training_size = len(data)
        LOGGER.info("NLP model trained with %s seed transactions", self.training_size)

    def predict(self, description: str) -> Dict[str, object]:
        if not self.model or not self.vectorizer or not clean_text(description):
            return {"category": "Unknown", "confidence": 0.0}
        probabilities = self.model.predict_proba(self.vectorizer.transform([self._model_text(description)]))[0]
        index = int(probabilities.argmax())
        return {"category": _canonical_label(str(self.model.classes_[index])), "confidence": float(probabilities[index])}

    def _model_text(self, description: str) -> str:
        return model_text(description, self.use_entity_features)

    def evaluate(self, descriptions: Iterable[str], labels: Iterable[str]) -> Dict[str, object]:
        from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
        actual = list(labels)
        predicted = [self.predict(description)["category"] for description in descriptions]
        return {
            "accuracy": accuracy_score(actual, predicted),
            "precision": precision_score(actual, predicted, average="weighted", zero_division=0),
            "recall": recall_score(actual, predicted, average="weighted", zero_division=0),
            "f1": f1_score(actual, predicted, average="weighted", zero_division=0),
            "labels": sorted(set(actual) | set(predicted)),
            "confusion_matrix": confusion_matrix(actual, predicted, labels=sorted(set(actual) | set(predicted))).tolist(),
            "sample_size": len(actual),
        }

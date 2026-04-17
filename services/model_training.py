from pathlib import Path
from typing import List, Tuple

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split

from config import CLASSIFIER_MODEL_PATH, VECTORIZER_PATH


def synthetic_training_data() -> Tuple[List[str], List[str]]:
    texts = [
        "connection timeout while calling auth service",
        "database deadlock detected on transaction",
        "user login completed successfully",
        "cache miss for session key",
        "null pointer exception in payment module",
        "disk utilization above threshold",
        "http 500 internal server error",
        "configuration loaded successfully",
        "api request latency warning exceeded",
        "critical memory allocation failed",
        "debug trace for request interceptor",
    ]
    labels = [
        "ERROR",
        "ERROR",
        "INFO",
        "INFO",
        "CRITICAL",
        "WARNING",
        "ERROR",
        "INFO",
        "WARNING",
        "CRITICAL",
        "INFO",
    ]
    return texts, labels


def train_and_save_classifier(
    model_path: Path = CLASSIFIER_MODEL_PATH, vectorizer_path: Path = VECTORIZER_PATH
) -> dict:
    texts, labels = synthetic_training_data()
    x_train, x_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.3, random_state=42, stratify=labels
    )

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=5000)
    x_train_vec = vectorizer.fit_transform(x_train)
    x_test_vec = vectorizer.transform(x_test)

    model = LogisticRegression(max_iter=1000)
    model.fit(x_train_vec, y_train)
    preds = model.predict(x_test_vec)

    metrics = {
        "accuracy": round(float(accuracy_score(y_test, preds)), 4),
        "f1_score": round(float(f1_score(y_test, preds, average="weighted")), 4),
    }

    joblib.dump(model, model_path)
    joblib.dump(vectorizer, vectorizer_path)
    return metrics

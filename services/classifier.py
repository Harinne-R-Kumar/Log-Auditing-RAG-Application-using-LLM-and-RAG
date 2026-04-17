import re
from pathlib import Path
from typing import Dict, List

import joblib

from config import CLASSIFIER_MODEL_PATH, VECTORIZER_PATH
from services.grok_client import GrokClient
from services.model_training import train_and_save_classifier


REGEX_RULES = {
    "CRITICAL": [
        r"out of memory",
        r"critical",
        r"segmentation fault",
        r"panic",
        r"fatal",
    ],
    "ERROR": [r"error", r"exception", r"failed", r"timeout", r"http 5\d\d"],
    "WARNING": [r"warn", r"latency", r"degraded", r"retry"],
    "INFO": [r"success", r"started", r"connected", r"healthy", r"completed"],
}


class HybridClassifier:
    def __init__(self) -> None:
        self.grok = GrokClient()
        self.model = None
        self.vectorizer = None
        self.metrics = {"accuracy": None, "f1_score": None}
        self._load_or_train()

    def _load_or_train(self) -> None:
        if not Path(CLASSIFIER_MODEL_PATH).exists() or not Path(VECTORIZER_PATH).exists():
            self.metrics = train_and_save_classifier()
        self.model = joblib.load(CLASSIFIER_MODEL_PATH)
        self.vectorizer = joblib.load(VECTORIZER_PATH)

    def regex_classify(self, message: str) -> str:
        msg = message.lower()
        for severity, patterns in REGEX_RULES.items():
            for pattern in patterns:
                if re.search(pattern, msg):
                    return severity
        return "UNKNOWN"

    def ml_classify(self, message: str) -> str:
        vec = self.vectorizer.transform([message])
        return str(self.model.predict(vec)[0])

    def llm_classify(self, message: str) -> str:
        prompt = (
            "Classify this log into one label among INFO, WARNING, ERROR, CRITICAL. "
            f"Log: {message}. Return only label."
        )
        output = self.grok.generate(prompt, temperature=0)
        if not output:
            return "INFO"
        label = output.strip().upper().split()[0]
        if label == "WARN":
            label = "WARNING"
        if label not in {"INFO", "WARNING", "ERROR", "CRITICAL"}:
            return "INFO"
        return label

    def classify_logs(self, logs: List[Dict]) -> List[Dict]:
        for log in logs:
            if log.get("severity") in {"INFO", "WARNING", "ERROR", "CRITICAL"}:
                log["severity_source"] = "input"
                continue

            regex_result = self.regex_classify(log["message"])
            if regex_result != "UNKNOWN":
                log["severity"] = regex_result
                log["severity_source"] = "regex"
                continue

            ml_result = self.ml_classify(log["message"])
            if ml_result:
                log["severity"] = ml_result
                log["severity_source"] = "ml"
                continue

            log["severity"] = self.llm_classify(log["message"])
            log["severity_source"] = "grok"
        return logs

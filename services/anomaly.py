from typing import Dict, List

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer


def detect_anomalies(logs: List[Dict]) -> Dict:
    if not logs:
        return {"anomaly_count": 0, "anomalies": []}

    messages = [log.get("message", "") for log in logs]
    vectorizer = TfidfVectorizer(max_features=3000)
    x = vectorizer.fit_transform(messages).toarray()

    clf = IsolationForest(contamination=0.08, random_state=42)
    preds = clf.fit_predict(x)
    scores = clf.decision_function(x)

    anomalies = []
    for log, pred, score in zip(logs, preds, scores):
        anomaly_score = float(-score)
        log["anomaly_score"] = round(anomaly_score, 4)
        log["is_anomaly"] = bool(pred == -1)
        if log["is_anomaly"]:
            anomalies.append(
                {
                    "timestamp": log.get("timestamp"),
                    "message": log.get("message"),
                    "severity": log.get("severity"),
                    "module": log.get("module"),
                    "anomaly_score": log["anomaly_score"],
                }
            )

    return {
        "anomaly_count": int(np.sum(np.array(preds) == -1)),
        "anomalies": anomalies,
    }

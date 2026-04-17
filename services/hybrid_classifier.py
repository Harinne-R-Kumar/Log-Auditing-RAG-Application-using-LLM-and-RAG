import re
from pathlib import Path
from typing import Dict, List

import joblib

from config import CLASSIFIER_MODEL_PATH, VECTORIZER_PATH
from services.grok_client import GrokClient

# Suppress warnings and try to import PyTorch, fall back to scikit-learn if not available
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.model_selection import train_test_split
    PYTORCH_AVAILABLE = True
    # Suppress PyTorch warnings
    torch.utils.backcompat.broadcast_warning.ignore = True
except ImportError:
    from sklearn.linear_model import LogisticRegression
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.model_selection import train_test_split
    PYTORCH_AVAILABLE = False

# PyTorch Neural Network (only if PyTorch is available)
if PYTORCH_AVAILABLE:
    class LogClassifier(nn.Module):
        def __init__(self, input_size: int, hidden_size: int = 128, num_classes: int = 4):
            super(LogClassifier, self).__init__()
            self.fc1 = nn.Linear(input_size, hidden_size)
            self.relu = nn.ReLU()
            self.dropout = nn.Dropout(0.3)
            self.fc2 = nn.Linear(hidden_size, hidden_size // 2)
            self.fc3 = nn.Linear(hidden_size // 2, num_classes)
            
        def forward(self, x):
            out = self.fc1(x)
            out = self.relu(out)
            out = self.dropout(out)
            out = self.fc2(out)
            out = self.relu(out)
            out = self.dropout(out)
            out = self.fc3(out)
            return out


class HybridClassifier:
    def __init__(self) -> None:
        self.grok = GrokClient()
        self.model = None
        self.vectorizer = None
        self.metrics = {"accuracy": None, "f1_score": None}
        self.use_pytorch = PYTORCH_AVAILABLE
        
        if self.use_pytorch:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self.label_to_idx = {"INFO": 0, "WARNING": 1, "ERROR": 2, "CRITICAL": 3}
            self.idx_to_label = {v: k for k, v in self.label_to_idx.items()}
        
        self._load_or_train()

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

    def _load_or_train(self) -> None:
        if self.use_pytorch:
            model_path = Path(CLASSIFIER_MODEL_PATH).with_suffix('.pt')
            if not model_path.exists() or not Path(VECTORIZER_PATH).exists():
                self.metrics = self._train_pytorch_classifier()
            
            # Load vectorizer
            self.vectorizer = joblib.load(VECTORIZER_PATH)
            
            # Load PyTorch model
            input_size = self.vectorizer.get_feature_names_out().shape[0]
            self.model = LogClassifier(input_size).to(self.device)
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
            self.model.eval()
        else:
            # Use scikit-learn
            if not Path(CLASSIFIER_MODEL_PATH).exists() or not Path(VECTORIZER_PATH).exists():
                self.metrics = self._train_sklearn_classifier()
            self.model = joblib.load(CLASSIFIER_MODEL_PATH)
            self.vectorizer = joblib.load(VECTORIZER_PATH)

    def _train_sklearn_classifier(self) -> dict:
        texts, labels = self._synthetic_training_data()
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

        joblib.dump(model, CLASSIFIER_MODEL_PATH)
        joblib.dump(vectorizer, VECTORIZER_PATH)
        return metrics

    def _train_pytorch_classifier(self) -> dict:
        texts, labels = self._synthetic_training_data()
        x_train, x_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.3, random_state=42, stratify=labels
        )

        # Vectorize text
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=5000)
        x_train_vec = vectorizer.fit_transform(x_train).toarray()
        x_test_vec = vectorizer.transform(x_test).toarray()

        # Convert to PyTorch tensors
        x_train_tensor = torch.FloatTensor(x_train_vec)
        x_test_tensor = torch.FloatTensor(x_test_vec)
        
        # Convert labels to indices
        y_train_idx = [self.label_to_idx[label] for label in y_train]
        y_test_idx = [self.label_to_idx[label] for label in y_test]
        y_train_tensor = torch.LongTensor(y_train_idx)
        y_test_tensor = torch.LongTensor(y_test_idx)

        # Initialize model
        input_size = x_train_vec.shape[1]
        model = LogClassifier(input_size).to(self.device)
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=0.001)

        # Training
        num_epochs = 50  # Reduced for faster training
        batch_size = 8
        model.train()
        
        for epoch in range(num_epochs):
            for i in range(0, len(x_train_tensor), batch_size):
                batch_x = x_train_tensor[i:i+batch_size].to(self.device)
                batch_y = y_train_tensor[i:i+batch_size].to(self.device)
                
                optimizer.zero_grad()
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()

        # Evaluation
        model.eval()
        with torch.no_grad():
            x_test_tensor = x_test_tensor.to(self.device)
            y_test_tensor = y_test_tensor.to(self.device)
            outputs = model(x_test_tensor)
            _, predicted = torch.max(outputs.data, 1)
            
            # Convert back to original labels
            predicted_labels = [self.idx_to_label[idx.item()] for idx in predicted.cpu()]
            y_test_labels = [self.idx_to_label[idx.item()] for idx in y_test_tensor.cpu()]

        metrics = {
            "accuracy": round(float(accuracy_score(y_test_labels, predicted_labels)), 4),
            "f1_score": round(float(f1_score(y_test_labels, predicted_labels, average="weighted")), 4),
        }

        # Save models
        torch.save(model.state_dict(), Path(CLASSIFIER_MODEL_PATH).with_suffix('.pt'))
        joblib.dump(vectorizer, VECTORIZER_PATH)
        
        return metrics

    def _synthetic_training_data(self):
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

    def regex_classify(self, message: str) -> str:
        msg = message.lower()
        for severity, patterns in self.REGEX_RULES.items():
            for pattern in patterns:
                if re.search(pattern, msg):
                    return severity
        return "UNKNOWN"

    def ml_classify(self, message: str) -> str:
        if self.use_pytorch:
            vec = self.vectorizer.transform([message]).toarray()
            tensor = torch.FloatTensor(vec).to(self.device)
            
            self.model.eval()
            with torch.no_grad():
                output = self.model(tensor)
                _, predicted = torch.max(output.data, 1)
                return self.idx_to_label[predicted.cpu().item()]
        else:
            # Use scikit-learn
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
                log["severity_source"] = "pytorch" if self.use_pytorch else "sklearn"
                continue

            log["severity"] = self.llm_classify(log["message"])
            log["severity_source"] = "grok"
        return logs

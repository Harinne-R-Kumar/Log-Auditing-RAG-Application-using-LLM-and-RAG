import json
from pathlib import Path
from typing import Dict, List

import faiss
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from config import PAST_LOG_DB


class RagRetriever:
    def __init__(self, db_path: Path = PAST_LOG_DB) -> None:
        self.db_path = db_path
        self.docs: List[Dict] = []
        self.vectorizer = TfidfVectorizer(max_features=4000)
        self.index = None
        self.doc_vectors = None
        self._load()

    def _load(self) -> None:
        self.docs = []
        if self.db_path.exists():
            with self.db_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.docs.append(json.loads(line))
        self._build_index()

    def _build_index(self) -> None:
        if not self.docs:
            self.index = None
            self.doc_vectors = None
            return
        texts = [d.get("message", "") for d in self.docs]
        tfidf = self.vectorizer.fit_transform(texts).toarray().astype("float32")
        self.doc_vectors = tfidf
        self.index = faiss.IndexFlatL2(tfidf.shape[1])
        self.index.add(tfidf)

    def add_logs(self, logs: List[Dict]) -> None:
        if not logs:
            return
        with self.db_path.open("a", encoding="utf-8") as f:
            for log in logs:
                f.write(json.dumps(log) + "\n")
        self._load()

    def query(self, query_text: str, k: int = 5) -> List[Dict]:
        if not self.index or not self.docs:
            return []
        query_vec = self.vectorizer.transform([query_text]).toarray().astype("float32")
        distances, indices = self.index.search(query_vec, min(k, len(self.docs)))
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < 0:
                continue
            doc = dict(self.docs[idx])
            doc["distance"] = float(dist)
            results.append(doc)
        return results

import os
from pathlib import Path

try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        return False

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

UPLOAD_FOLDER = BASE_DIR / "uploads"
MODEL_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"
PAST_LOG_DB = DATA_DIR / "past_logs.jsonl"
FEEDBACK_DB = DATA_DIR / "feedback.jsonl"
CLASSIFIER_MODEL_PATH = MODEL_DIR / "hybrid_classifier.joblib"
VECTORIZER_PATH = MODEL_DIR / "tfidf_vectorizer.joblib"

ALLOWED_EXTENSIONS = {"log", "txt", "csv"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

GROK_API_URL = os.getenv("GROK_API_URL") or os.getenv(
    "GROQ_API_URL", "https://api.x.ai/v1/chat/completions"
)
# Support both GROK_API_KEY and common typo/alternate key GROQ_API_KEY.
GROK_API_KEY = os.getenv("GROK_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
GROK_MODEL = os.getenv("GROK_MODEL") or os.getenv("GROQ_MODEL", "grok-2-latest")

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")


def ensure_directories() -> None:
    for path in [UPLOAD_FOLDER, MODEL_DIR, DATA_DIR]:
        path.mkdir(parents=True, exist_ok=True)

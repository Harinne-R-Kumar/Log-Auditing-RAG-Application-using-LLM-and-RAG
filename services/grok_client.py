from typing import Optional

import requests

from config import GROK_API_KEY, GROK_API_URL, GROK_MODEL


class GrokClient:
    def __init__(self) -> None:
        self.api_key = GROK_API_KEY
        self.api_url = GROK_API_URL
        self.model = GROK_MODEL
        self.last_error: Optional[str] = None

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, temperature: float = 0.2) -> Optional[str]:
        if not self.enabled:
            self.last_error = "Missing API key"
            return None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an expert log analysis assistant."},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        }
        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=30)
            if response.status_code >= 400:
                body = response.text[:300]
                self.last_error = f"HTTP {response.status_code}: {body}"
                return None
            data = response.json()
            self.last_error = None
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            self.last_error = str(exc)
            return None

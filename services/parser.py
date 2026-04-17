import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from dateutil import parser as date_parser


TIMESTAMP_REGEX = re.compile(
    r"(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:,\d+|\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)"
)
SEVERITY_REGEX = re.compile(r"\b(INFO|WARNING|WARN|ERROR|CRITICAL|DEBUG)\b", re.IGNORECASE)
MODULE_REGEX = re.compile(r"(?:module|service|func|function|component)=([A-Za-z0-9_.-]+)")


def _normalize_severity(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.upper()
    if value == "WARN":
        value = "WARNING"
    return value


def _extract_timestamp(text: str) -> Optional[datetime]:
    match = TIMESTAMP_REGEX.search(text)
    if not match:
        return None
    try:
        return date_parser.parse(match.group(1))
    except Exception:
        return None


def _extract_severity(text: str) -> Optional[str]:
    match = SEVERITY_REGEX.search(text)
    return _normalize_severity(match.group(1)) if match else None


def _extract_module(text: str) -> Optional[str]:
    mod_match = MODULE_REGEX.search(text)
    if mod_match:
        return mod_match.group(1)
    if "." in text:
        token = text.split()[0]
        if "." in token and len(token) < 60:
            return token.strip(":")
    tokens = text.split()
    if tokens:
        first = tokens[0].strip(":[]")
        if re.match(r"^[A-Za-z][A-Za-z0-9_-]{2,}$", first):
            return first
    return None


def _parse_line(line: str, line_number: int) -> Dict:
    ts = _extract_timestamp(line)
    severity = _extract_severity(line)
    module = _extract_module(line)
    message = line.strip()
    return {
        "line_number": line_number,
        "timestamp": ts.isoformat() if ts else None,
        "message": message,
        "severity": severity,
        "module": module or "unknown",
    }


def parse_log_file(file_path: Path) -> List[Dict]:
    suffix = file_path.suffix.lower()
    parsed_logs: List[Dict] = []

    if suffix == ".csv":
        with file_path.open("r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=1):
                raw = " ".join([str(v) for v in row.values() if v is not None])
                entry = _parse_line(raw, idx)
                normalized = {str(k).strip().lower(): v for k, v in row.items() if k is not None}

                timestamp_value = (
                    normalized.get("timestamp")
                    or normalized.get("time")
                    or normalized.get("datetime")
                    or normalized.get("date")
                )
                if timestamp_value:
                    try:
                        entry["timestamp"] = date_parser.parse(str(timestamp_value)).isoformat()
                    except Exception:
                        pass

                severity_value = (
                    normalized.get("severity")
                    or normalized.get("level")
                    or normalized.get("loglevel")
                    or normalized.get("priority")
                )
                if severity_value:
                    entry["severity"] = _normalize_severity(str(severity_value))

                message_value = (
                    normalized.get("message")
                    or normalized.get("log")
                    or normalized.get("event")
                    or normalized.get("description")
                )
                if message_value:
                    entry["message"] = str(message_value)

                module_value = (
                    normalized.get("module")
                    or normalized.get("service")
                    or normalized.get("function")
                    or normalized.get("component")
                    or normalized.get("source")
                )
                if module_value:
                    entry["module"] = str(module_value)
                parsed_logs.append(entry)
    else:
        with file_path.open("r", encoding="utf-8", errors="ignore") as f:
            for idx, line in enumerate(f, start=1):
                if line.strip():
                    parsed_logs.append(_parse_line(line, idx))

    if not parsed_logs:
        return []

    df = pd.DataFrame(parsed_logs)
    if "timestamp" in df:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        if df["timestamp"].isna().all():
            start = pd.Timestamp.utcnow().floor("min")
            df["timestamp"] = [start + pd.Timedelta(minutes=i) for i in range(len(df))]
        df["timestamp"] = df["timestamp"].astype("string")
        parsed_logs = df.to_dict(orient="records")

    return parsed_logs

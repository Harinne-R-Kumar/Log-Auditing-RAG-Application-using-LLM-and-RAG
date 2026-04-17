from typing import Dict, List

import pandas as pd


def build_time_analysis(logs: List[Dict]) -> Dict:
    if not logs:
        return {
            "logs_per_hour": {},
            "logs_per_day": {},
            "peak_error_time": None,
            "spike_intervals": [],
        }
    df = pd.DataFrame(logs)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"])

    if df.empty:
        return {
            "logs_per_hour": {},
            "logs_per_day": {},
            "peak_error_time": None,
            "spike_intervals": [],
        }

    per_hour = (
        df.set_index("timestamp")
        .resample("h")
        .size()
        .rename("count")
        .reset_index()
        .assign(timestamp=lambda d: d["timestamp"].astype(str))
    )
    per_day = (
        df.set_index("timestamp")
        .resample("d")
        .size()
        .rename("count")
        .reset_index()
        .assign(timestamp=lambda d: d["timestamp"].astype(str))
    )

    errors = df[df["severity"].isin(["ERROR", "CRITICAL"])]
    peak_error_time = None
    spike_intervals: List[Dict] = []
    if not errors.empty:
        error_hour = errors.set_index("timestamp").resample("h").size().rename("count").reset_index()
        peak_row = error_hour.sort_values("count", ascending=False).iloc[0]
        peak_error_time = str(peak_row["timestamp"])
        threshold = error_hour["count"].mean() + error_hour["count"].std(ddof=0)
        spike_intervals = error_hour[error_hour["count"] >= threshold].assign(
            timestamp=lambda d: d["timestamp"].astype(str)
        ).to_dict(orient="records")

    return {
        "logs_per_hour": per_hour.to_dict(orient="records"),
        "logs_per_day": per_day.to_dict(orient="records"),
        "peak_error_time": peak_error_time,
        "spike_intervals": spike_intervals,
    }


def build_timeline(logs: List[Dict]) -> List[Dict]:
    ordered = sorted(logs, key=lambda x: (x.get("timestamp") or "", x.get("line_number") or 0))
    timeline = []
    for idx, log in enumerate(ordered, start=1):
        timeline.append(
            {
                "event_id": idx,
                "timestamp": log.get("timestamp"),
                "module": log.get("module"),
                "severity": log.get("severity"),
                "message": log.get("message"),
            }
        )
    return timeline

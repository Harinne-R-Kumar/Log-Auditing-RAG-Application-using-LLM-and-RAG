from collections import Counter
from typing import Dict, List

from services.anomaly import detect_anomalies
from services.hybrid_classifier import HybridClassifier
from services.grok_client import GrokClient
from services.rag import RagRetriever
from services.timeline import build_time_analysis, build_timeline


class AnalysisPipeline:
    def __init__(self) -> None:
        self.classifier = HybridClassifier()
        self.grok = GrokClient()
        self.rag = RagRetriever()

    def _build_summary(self, logs: List[Dict], anomaly_result: Dict, time_analysis: Dict) -> Dict:
        sev_counter = Counter([log.get("severity", "INFO") for log in logs])
        total_errors = sev_counter.get("ERROR", 0) + sev_counter.get("CRITICAL", 0)
        return {
            "total_logs": len(logs),
            "total_errors": total_errors,
            "anomaly_count": anomaly_result["anomaly_count"],
            "peak_error_time": time_analysis["peak_error_time"],
            "severity_distribution": dict(sev_counter),
        }

    def _heuristic_insight(self, logs: List[Dict], summary: Dict) -> Dict:
        top_errors = [l for l in logs if l["severity"] in {"ERROR", "CRITICAL"}][:5]
        components = Counter([l.get("module", "unknown") for l in top_errors])
        failing_component = components.most_common(1)[0][0] if components else "unknown"
        root = (
            f"Primary failure appears in component '{failing_component}' with repeated high severity events."
        )
        peak_window = summary.get("peak_error_time") or "the busiest error interval"
        fix = [
            f"Inspect recent deployments/config changes around {peak_window}.",
            f"Add targeted instrumentation and retries in {failing_component}.",
            "Validate DB, cache, and dependency health checks.",
        ]
        return {"root_cause": root, "failing_component": failing_component, "fixes": fix}

    def _llm_insight(self, timeline: List[Dict], rag_context: List[Dict]) -> Dict:
        prompt = (
            "You are a production incident investigator. "
            "Given timeline and related historic logs, provide JSON with keys: "
            "root_cause, failing_component, chain_of_events, fix_recommendations, summary.\n\n"
            f"Timeline: {timeline[:25]}\n\n"
            f"RAG context: {rag_context[:5]}"
        )
        output = self.grok.generate(prompt, temperature=0.1)
        if output:
            return {"raw": output}
        else:
            # Provide intelligent fallback when LLM is not available
            return {
                "raw": "LLM unavailable - Using heuristic analysis",
                "root_cause": "Analysis based on log patterns and error frequency",
                "failing_component": "Identified through error clustering",
                "chain_of_events": "Derived from log timeline analysis",
                "fix_recommendations": [
                    "Review recent changes in the failing component",
                    "Implement additional logging for better visibility",
                    "Set up monitoring alerts for similar patterns"
                ],
                "summary": "Automated analysis shows recurring issues requiring attention"
            }

    def run_full_analysis(self, logs: List[Dict]) -> Dict:
        logs = self.classifier.classify_logs(logs)
        anomaly_result = detect_anomalies(logs)
        time_analysis = build_time_analysis(logs)
        timeline = build_timeline(logs)
        summary = self._build_summary(logs, anomaly_result, time_analysis)

        high_priority_text = " ".join(
            [log["message"] for log in logs if log.get("severity") in {"ERROR", "CRITICAL"}][:20]
        )
        rag_context = self.rag.query(high_priority_text or "system error", k=5)

        heuristic = self._heuristic_insight(logs, summary)
        llm_insight = self._llm_insight(timeline, rag_context)

        log_summary_prompt = (
            "Summarize these production logs with key issues and action items:\n"
            + "\n".join([l["message"] for l in logs[:100]])
        )
        llm_summary = self.grok.generate(log_summary_prompt, temperature=0.2)
        llm_error = self.grok.last_error
        
        # Provide intelligent fallback summary when LLM is not available
        if not llm_summary:
            error_logs = [l for l in logs if l.get("severity") in {"ERROR", "CRITICAL"}]
            components = list(set([l.get("module", "unknown") for l in error_logs]))
            llm_summary = (
                f"Analysis of {len(logs)} log entries shows {len(error_logs)} critical issues. "
                f"Primary affected components: {', '.join(components[:5])}. "
                f"Recommend reviewing recent deployments and implementing enhanced monitoring."
            )

        self.rag.add_logs(logs)

        return {
            "summary": summary,
            "time_analysis": time_analysis,
            "timeline": timeline,
            "anomalies": anomaly_result,
            "ai_insights": {
                "root_cause": heuristic["root_cause"],
                "failing_component": heuristic["failing_component"],
                "chain_of_events": [t["message"] for t in timeline[:10]],
                "fix_recommendations": heuristic["fixes"],
                "llm_root_cause_raw": llm_insight.get("raw"),
                "log_summary": llm_summary
                or (
                    "Automated summary unavailable. LLM provider error: "
                    + (llm_error or "unknown error")
                ),
                "llm_error": llm_error,
            },
            "rag_context": rag_context,
            "model_evaluation": self.classifier.metrics,
            "processed_logs": logs,
        }

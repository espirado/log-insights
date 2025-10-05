from typing import List, Dict, Any
import time
import requests
from datetime import datetime
from .base import BaseAnalyzer


class OllamaAnalyzer(BaseAnalyzer):
    """Analyzer backed by a local Ollama model, matching the JSON contract.

    Requires an Ollama server running locally (default http://localhost:11434).
    """

    def __init__(self, model: str = "llama3.1:8b", host: str = "http://localhost:11434"):
        super().__init__()
        self.model = model
        self.host = host.rstrip("/")

    def process_stream(self, log_stream: Any):
        raise NotImplementedError("Real-time stream processing not implemented yet")

    def _build_prompt(self, logs: List[str]) -> str:
        return (
            "As an experienced SRE, analyze these logs and return STRICT JSON with keys: "
            "context (Kubernetes|Database|Infrastructure|Application|Security), "
            "category (CPU|Memory|Network|Storage|Security|Application|Database), severity (Critical|High|Medium|Low), "
            "component, root_cause, remediation, timestamp (ISO-8601).\n"
            "Ensure schema compliance and concise, technical fields.\n"
            f"Logs:\n{chr(10).join(logs)}"
        )

    def analyze_chunk(self, logs: List[str]) -> Dict[str, Any]:
        start_time = time.time()
        prompt = self._build_prompt(logs)
        try:
            resp = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "num_predict": 512
                    }
                },
                timeout=120
            )
            resp.raise_for_status()
            data = resp.json() or {}
            content = data.get("response", "{}")
            analysis = self._parse_and_validate(content)
            self._update_results(analysis)
            self.processing_time += time.time() - start_time
            return analysis
        except Exception:
            return self._get_error_analysis()

    def _parse_and_validate(self, content: str) -> Dict[str, Any]:
        import json
        try:
            obj = json.loads(content)
        except Exception:
            obj = {}
        # Fill required fields
        obj.setdefault("context", "Unknown")
        obj.setdefault("category", "Unknown")
        obj.setdefault("severity", "Unknown")
        obj.setdefault("component", "Unknown")
        obj.setdefault("root_cause", "")
        obj.setdefault("remediation", "")
        # Normalize timestamp to ISO if invalid
        ts = obj.get("timestamp")
        try:
            import dateutil.parser as _dp  # type: ignore
            _ = _dp.parse(ts) if ts else None
        except Exception:
            obj["timestamp"] = datetime.now().isoformat()
        # Heuristic confidence
        obj["confidence_score"] = self._estimate_confidence(obj)
        return obj

    def _estimate_confidence(self, analysis: Dict[str, Any]) -> float:
        score = 1.0
        for key in ["category", "severity", "root_cause", "remediation"]:
            if not analysis.get(key):
                score *= 0.8
        if len((analysis.get("root_cause") or "")) < 40:
            score *= 0.9
        if len((analysis.get("remediation") or "")) < 40:
            score *= 0.9
        ctx = (analysis.get("context") or "").lower()
        if ctx not in ["kubernetes", "database", "infrastructure", "application", "security"]:
            score *= 0.9
        return max(0.05, round(score, 3))

    def _get_error_analysis(self) -> Dict[str, Any]:
        return {
            'context': 'Unknown',
            'category': 'Unknown',
            'severity': 'Unknown',
            'component': 'Unknown',
            'root_cause': 'Analysis failed',
            'remediation': 'Manual investigation required',
            'timestamp': datetime.now().isoformat(),
            'confidence_score': 0.1,
        }

    def _update_results(self, analysis: Dict[str, Any]):
        context = analysis.get('context', 'Unknown')
        category = analysis.get('category', 'Unknown')
        severity = analysis.get('severity', 'Unknown')
        self.results['issues'][context] = self.results['issues'].get(context, 0) + 1
        self.results['severities'][severity] = self.results['severities'].get(severity, 0) + 1
        self.results['timeline'].append({
            'timestamp': analysis.get('timestamp', datetime.now().isoformat()),
            'context': context,
            'category': category,
            'component': analysis.get('component', 'Unknown'),
            'severity': severity,
            'root_cause': analysis.get('root_cause', ''),
            'remediation': analysis.get('remediation', '')
        })




"""
Structured Machine-Readable Observability Logger for AI MV Director Platform
"""

from __future__ import annotations
import os
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any


@dataclass
class StructuredDirectorLog:
    timestamp: float
    project_id: str
    scene_id: Optional[str]
    shot_id: Optional[str]
    take_id: Optional[str]
    operation: str
    provider: str
    model: str
    decision: str
    reason: str
    cost_estimate_twd: float
    actual_cost_twd: float
    qa_score: Optional[float]
    trace_id: str
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


class DirectorObservability:
    """Structured Logging & Audit Tracing Engine."""

    def __init__(self, log_dir: str = "logs/director"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, "director_events.jsonl")

    def log(
        self,
        project_id: str,
        operation: str,
        decision: str,
        reason: str,
        scene_id: Optional[str] = None,
        shot_id: Optional[str] = None,
        take_id: Optional[str] = None,
        provider: str = "gemini",
        model: str = "veo-3.1-fast-generate-preview",
        cost_estimate_twd: float = 0.0,
        actual_cost_twd: float = 0.0,
        qa_score: Optional[float] = None,
        trace_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> StructuredDirectorLog:
        entry = StructuredDirectorLog(
            timestamp=time.time(),
            project_id=project_id,
            scene_id=scene_id,
            shot_id=shot_id,
            take_id=take_id,
            operation=operation,
            provider=provider,
            model=model,
            decision=decision,
            reason=reason,
            cost_estimate_twd=cost_estimate_twd,
            actual_cost_twd=actual_cost_twd,
            qa_score=qa_score,
            trace_id=trace_id or f"tr_{int(time.time()*1000)}",
            extra=extra or {},
        )
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(entry.to_json() + "\n")
        except Exception:
            pass
        return entry

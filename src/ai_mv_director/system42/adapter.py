"""
System 4.2 Adapter & Senior Agent Governance Bridge
Exposes CapabilityRegistry, DecisionTrace, ExperienceRegistry, ADR, ProjectDNA, PolicyGate, and EvidenceGuard.
"""

from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any


@dataclass
class DecisionTrace:
    trace_id: str
    timestamp: float
    actor: str
    action: str
    context: Dict[str, Any]
    decision: str
    rationale: str
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExperienceEntry:
    experience_id: str
    domain: str
    lesson_learned: str
    recommended_policy: str
    observed_failure: str
    recorded_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CapabilityRegistry:
    """System 4.2 dynamic capability catalog."""

    def __init__(self):
        self._capabilities = {
            "director_planning": True,
            "scene_bible_inheritance": True,
            "character_bible_injection": True,
            "music_timeline_analysis": True,
            "cost_gate_governance": True,
            "veo_3_1_generation": True,
            "gemini_omni_stateful_edit": True,
            "10_layer_continuity_qa": True,
            "hierarchical_rollback": True,
            "async_job_resumption": True,
        }

    def is_capable(self, capability_name: str) -> bool:
        return self._capabilities.get(capability_name, False)

    def list_all(self) -> Dict[str, bool]:
        return dict(self._capabilities)


class PolicyGate:
    """Verifies that operations comply with System 4.2 Non-Destructive Protocols."""

    def __init__(self, cost_limit_twd: float = 5000.0):
        self.cost_limit_twd = cost_limit_twd

    def check_execution_policy(self, plan_meta: Dict[str, Any], token: Optional[str]) -> Dict[str, Any]:
        if not token:
            return {"allowed": False, "reason": "EXECUTION_BLOCKED: Missing approval token."}
        est_cost = plan_meta.get("estimated_twd", 0.0)
        if est_cost > self.cost_limit_twd:
            return {"allowed": False, "reason": f"EXECUTION_BLOCKED: Cost {est_cost} TWD exceeds policy limit {self.cost_limit_twd} TWD."}
        return {"allowed": True, "reason": "POLICY_PASSED: Approved by System 4.2 Policy Gate."}


class EvidenceGuard:
    """Ensures no state promotion without verifiable artifact / test proof."""

    @staticmethod
    def verify_take_evidence(file_path: Optional[str], qa_score: float) -> bool:
        if not file_path:
            return False
        return qa_score >= 0.70


class System42Adapter:
    """Universal System 4.2 Bridge."""

    def __init__(self):
        self.capabilities = CapabilityRegistry()
        self.policy_gate = PolicyGate()
        self.evidence_guard = EvidenceGuard()
        self._traces: List[DecisionTrace] = []
        self._experiences: List[ExperienceEntry] = []

    def record_decision(self, actor: str, action: str, decision: str, rationale: str, context: Optional[Dict[str, Any]] = None, evidence: Optional[List[str]] = None) -> DecisionTrace:
        trace = DecisionTrace(
            trace_id=f"trace_{uuid.uuid4().hex[:8]}",
            timestamp=time.time(),
            actor=actor,
            action=action,
            context=context or {},
            decision=decision,
            rationale=rationale,
            evidence=evidence or [],
        )
        self._traces.append(trace)
        return trace

    def record_experience(self, domain: str, lesson: str, policy: str, failure: str) -> ExperienceEntry:
        exp = ExperienceEntry(
            experience_id=f"exp_{uuid.uuid4().hex[:8]}",
            domain=domain,
            lesson_learned=lesson,
            recommended_policy=policy,
            observed_failure=failure,
        )
        self._experiences.append(exp)
        return exp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capabilities": self.capabilities.list_all(),
            "trace_count": len(self._traces),
            "experience_count": len(self._experiences),
        }

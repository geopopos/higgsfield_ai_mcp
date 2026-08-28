"""
Cost Governance & Budget Gate for AI MV Director Platform
Enforces strict budget constraints, variance tracking, retry cost caps, and approval tokens.
"""

from __future__ import annotations
import os
import uuid
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any


class CostGateStatus(str, Enum):
    COST_OK = "COST_OK"
    COST_WARNING = "COST_WARNING"
    COST_BLOCKED = "COST_BLOCKED"


@dataclass
class CostAuditRecord:
    shot_id: str
    take_id: Optional[str]
    model: str
    resolution: str
    duration_sec: float
    estimated_twd: float
    actual_twd: float
    variance_twd: float
    is_mock: bool = True


@dataclass
class GateEvaluationResult:
    status: CostGateStatus
    approved: bool
    approval_token: Optional[str]
    estimated_total_twd: float
    allocated_budget_twd: float
    remaining_budget_twd: float
    warning_message: Optional[str] = None
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


class BudgetManager:
    """Tracks project spend, retry reserve, variance, and cumulative billable totals."""

    def __init__(self, max_budget_twd: float = 5000.0, warning_threshold_ratio: float = 0.80):
        self.max_budget_twd = float(os.environ.get("SESSION_BUDGET_TWD", max_budget_twd))
        self.warning_threshold_ratio = warning_threshold_ratio
        self.spent_twd = 0.0
        self.reserved_twd = 0.0
        self.audit_records: List[CostAuditRecord] = []

    def get_remaining_budget(self) -> float:
        return max(0.0, self.max_budget_twd - (self.spent_twd + self.reserved_twd))

    def record_actual_spend(
        self,
        shot_id: str,
        take_id: str,
        model: str,
        resolution: str,
        duration_sec: float,
        estimated_twd: float,
        actual_twd: float,
        is_mock: bool = True
    ) -> None:
        variance = actual_twd - estimated_twd
        if not is_mock:
            self.spent_twd += actual_twd
        self.audit_records.append(CostAuditRecord(
            shot_id=shot_id,
            take_id=take_id,
            model=model,
            resolution=resolution,
            duration_sec=duration_sec,
            estimated_twd=estimated_twd,
            actual_twd=actual_twd,
            variance_twd=variance,
            is_mock=is_mock,
        ))

    def get_summary(self) -> Dict[str, Any]:
        return {
            "max_budget_twd": self.max_budget_twd,
            "spent_twd": self.spent_twd,
            "remaining_twd": self.get_remaining_budget(),
            "audit_count": len(self.audit_records),
        }


class CostGate:
    """Quality & Budget Barrier before video generation."""

    def __init__(self, budget_manager: Optional[BudgetManager] = None):
        self.budget_manager = budget_manager or BudgetManager()
        self._active_tokens: Dict[str, Dict[str, Any]] = {}

    def evaluate_plan(self, estimated_total_twd: float, project_id: str) -> GateEvaluationResult:
        """Evaluate plan against budget and issue a cryptographic approval token."""
        remaining = self.budget_manager.get_remaining_budget()
        limit = self.budget_manager.max_budget_twd

        if estimated_total_twd > remaining or estimated_total_twd > limit:
            return GateEvaluationResult(
                status=CostGateStatus.COST_BLOCKED,
                approved=False,
                approval_token=None,
                estimated_total_twd=estimated_total_twd,
                allocated_budget_twd=limit,
                remaining_budget_twd=remaining,
                reason=f"Estimated plan cost ({estimated_total_twd} TWD) exceeds available budget ({remaining} TWD).",
            )

        # Warning zone
        is_warning = (estimated_total_twd / max(1.0, limit)) >= self.budget_manager.warning_threshold_ratio
        status = CostGateStatus.COST_WARNING if is_warning else CostGateStatus.COST_OK
        warning_msg = f"Plan uses {round(estimated_total_twd/limit*100, 1)}% of total budget." if is_warning else None

        token = f"approval_token_{uuid.uuid4().hex}"
        self._active_tokens[token] = {
            "project_id": project_id,
            "estimated_twd": estimated_total_twd,
            "status": status.value,
        }

        return GateEvaluationResult(
            status=status,
            approved=True,
            approval_token=token,
            estimated_total_twd=estimated_total_twd,
            allocated_budget_twd=limit,
            remaining_budget_twd=remaining,
            warning_message=warning_msg,
            reason=f"Budget verified ({status.value}). Approved for generation.",
        )

    def verify_token(self, token: str, project_id: str) -> bool:
        """Verify that an execution request has a valid dry-run approval token."""
        if not token or token not in self._active_tokens:
            return False
        rec = self._active_tokens[token]
        return rec.get("project_id") == project_id

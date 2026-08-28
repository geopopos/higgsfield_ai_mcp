"""
Intelligent Model Router for AI MV Director Platform
Deterministic, traceable multi-model routing across Veo 3.1, Fast, Lite, and Gemini Omni 1.1 Flash.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
try:
    from ..domain.shot import ShotClassification, ShotRecord
except ImportError:
    from ai_mv_director.domain.shot import ShotClassification, ShotRecord


@dataclass(frozen=True)
class RoutingDecision:
    provider: str
    model: str
    resolution: str
    duration_seconds: float
    estimated_cost_usd: float
    estimated_cost_twd: float
    reason: str
    trace_id: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ModelRouter:
    """Deterministic Model Routing Engine."""

    MODEL_VEO_STANDARD = "veo-3.1-generate-preview"
    MODEL_VEO_FAST = "veo-3.1-fast-generate-preview"
    MODEL_VEO_LITE = "veo-3.1-lite-generate-preview"
    MODEL_OMNI_FLASH = "gemini-omni-1.1-flash"

    USD_TWD_RATE = 32.0

    # Pricing per second (USD)
    PRICING = {
        MODEL_VEO_STANDARD: {"720p": 0.40, "1080p": 0.40, "4k": 0.60},
        MODEL_VEO_FAST: {"720p": 0.10, "1080p": 0.12, "4k": 0.30},
        MODEL_VEO_LITE: {"720p": 0.05, "1080p": 0.08, "4k": 0.00},
        MODEL_OMNI_FLASH: {"360p": 0.03, "720p": 0.10, "1080p": 0.15, "4k": 0.25},
    }

    def route_shot(
        self,
        classification: ShotClassification,
        quality_target: str = "fast",
        duration_sec: float = 8.0,
        resolution: Optional[str] = None,
        needs_stateful_edit: bool = False,
        needs_extension: bool = False,
        needs_first_last_frame: bool = False,
        reference_images_count: int = 0,
        budget_constrained: bool = False,
        trace_id: str = "",
    ) -> RoutingDecision:
        """Route shot to the optimal model deterministically with explainable rationale."""

        # 1. Specialized Omni Tasks (First/Last frame transition, stateful editing, 360p draft, extensions)
        if needs_stateful_edit:
            model = self.MODEL_OMNI_FLASH
            res = resolution or "720p"
            reason = "Routed to Gemini Omni 1.1 Flash for stateful multi-turn editing."
        elif needs_first_last_frame:
            model = self.MODEL_OMNI_FLASH
            res = resolution or "720p"
            reason = "Routed to Gemini Omni 1.1 Flash for First/Last frame transition interpolation."
        elif needs_extension:
            model = self.MODEL_OMNI_FLASH
            res = resolution or "720p"
            reason = "Routed to Gemini Omni 1.1 Flash for 10s context-aware scene extension."
        elif quality_target == "draft_360p":
            model = self.MODEL_OMNI_FLASH
            res = "360p"
            reason = "Routed to Gemini Omni 1.1 Flash for ultra-low-cost 360p draft exploration."
        elif quality_target in ("master_4k", "hero_4k") or classification == ShotClassification.HERO:
            model = self.MODEL_VEO_STANDARD
            res = resolution or "4k"
            reason = "Routed to Veo 3.1 Standard for Cinema Master / HERO 4K fidelity."
        elif budget_constrained or quality_target == "lite":
            model = self.MODEL_VEO_LITE
            res = resolution or "720p"
            reason = "Routed to Veo 3.1 Lite for budget-constrained rapid iteration."
        elif quality_target == "standard":
            model = self.MODEL_VEO_STANDARD
            res = resolution or "1080p"
            reason = "Routed to Veo 3.1 Standard for production quality."
        else:
            # Default production workhorse
            model = self.MODEL_VEO_FAST
            res = resolution or "720p"
            reason = "Routed to Veo 3.1 Fast for optimal balance of speed, cinematic motion, and cost."

        # Calculate estimated cost
        rate_per_sec = self.PRICING.get(model, {}).get(res, 0.10)
        cost_usd = round(rate_per_sec * duration_sec, 4)
        cost_twd = round(cost_usd * self.USD_TWD_RATE, 2)

        return RoutingDecision(
            provider="gemini",
            model=model,
            resolution=res,
            duration_seconds=duration_sec,
            estimated_cost_usd=cost_usd,
            estimated_cost_twd=cost_twd,
            reason=reason,
            trace_id=trace_id or f"trace_{model[:6]}",
        )

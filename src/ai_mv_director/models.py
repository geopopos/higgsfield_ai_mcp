from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass
class DirectorPolicy:
    max_budget_twd: float = 5000.0
    min_continuity_score: float = 0.45
    default_duration: int = 8
    draft_resolution: str = "720p"
    final_resolution: str = "1080p"
    aspect_ratio: str = "16:9"
    auto_activate: bool = False
    require_qa: bool = True
    max_parallel: int = 1

@dataclass
class ShotDecision:
    shot_id: str
    scene_id: str
    sequence_order: int
    prompt: str
    camera: str
    duration_seconds: int
    resolution: str
    aspect_ratio: str
    quality: str
    provider_model: str
    reference_images: list[str] = field(default_factory=list)
    transition: str = "cut"
    dialogue_script: str | None = None
    sfx_cues: str | None = None
    ambient_audio: str | None = None
    music_direction: str | None = None
    state: str = "planned"
    take_id: str | None = None
    error: str | None = None

    def to_dict(self): return asdict(self)

@dataclass
class MVProject:
    project_id: str
    title: str
    story: str
    status: str = "draft"
    aspect_ratio: str = "16:9"
    shots: list[ShotDecision] = field(default_factory=list)
    estimated_twd: float = 0.0
    spent_twd: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        d = asdict(self)
        d["shots"] = [s.to_dict() for s in self.shots]
        return d

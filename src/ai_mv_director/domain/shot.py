"""
Shot Domain Model & Classifications for AI MV Director Platform (Shot Planner 2.0)
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from .ids import generate_shot_id


class ShotClassification(str, Enum):
    ESTABLISHING = "ESTABLISHING"
    CHARACTER = "CHARACTER"
    PERFORMANCE = "PERFORMANCE"
    ACTION = "ACTION"
    EMOTIONAL = "EMOTIONAL"
    INSERT = "INSERT"
    TRANSITION = "TRANSITION"
    HERO = "HERO"


@dataclass
class ShotRecord:
    shot_id: str
    scene_id: str
    sequence_order: int
    duration_sec: float
    purpose: str
    classification: ShotClassification
    action: str
    characters: List[str] = field(default_factory=list)
    location: str = ""
    camera: str = "35mm prime"
    lens: str = "35mm f/1.8"
    movement: str = "Static / Slow Dolly"
    composition: str = "Rule of Thirds"
    lighting: str = "Cinematic natural"
    color: str = "Kodak film look"
    transition_in: str = "Cut"
    transition_out: str = "Cut"
    audio_cues: str = ""
    dialogue_script: str = ""
    visual_references: List[str] = field(default_factory=list)
    provider_constraints: Dict[str, Any] = field(default_factory=dict)
    negative_constraints: List[str] = field(default_factory=list)
    priority: int = 1  # 1 (Hero/Essential) to 3 (B-Roll)
    quality_target: str = "fast"  # "fast", "standard", "master_4k"
    estimated_cost_twd: float = 0.0
    selected_model: str = "veo-3.1-fast-generate-preview"
    resolution: str = "720p"
    state: str = "planned"  # "planned", "dry_run_approved", "queued", "generated", "active", "rejected"

    @classmethod
    def create(
        cls,
        scene_id: str,
        sequence_order: int,
        action: str,
        duration_sec: float = 8.0,
        purpose: str = "Narrative progression",
        classification: ShotClassification = ShotClassification.CHARACTER,
        characters: Optional[List[str]] = None,
        location: str = "",
        camera: str = "35mm prime",
        lens: str = "35mm f/1.8",
        movement: str = "Slow Dolly In",
        composition: str = "Medium Close-up",
        lighting: str = "Warm natural",
        color: str = "Cinematic natural",
        transition_in: str = "Cut",
        transition_out: str = "Cut",
        audio_cues: str = "",
        dialogue_script: str = "",
        visual_references: Optional[List[str]] = None,
        provider_constraints: Optional[Dict[str, Any]] = None,
        negative_constraints: Optional[List[str]] = None,
        priority: int = 1,
        quality_target: str = "fast",
    ) -> ShotRecord:
        shot_id = generate_shot_id(scene_id, sequence_order, action)
        return cls(
            shot_id=shot_id,
            scene_id=scene_id,
            sequence_order=sequence_order,
            duration_sec=duration_sec,
            purpose=purpose,
            classification=classification,
            action=action,
            characters=characters or [],
            location=location,
            camera=camera,
            lens=lens,
            movement=movement,
            composition=composition,
            lighting=lighting,
            color=color,
            transition_in=transition_in,
            transition_out=transition_out,
            audio_cues=audio_cues,
            dialogue_script=dialogue_script,
            visual_references=visual_references or [],
            provider_constraints=provider_constraints or {},
            negative_constraints=negative_constraints or [],
            priority=priority,
            quality_target=quality_target,
        )

    def compile_full_prompt(self, character_bible_text: str = "", scene_context: str = "") -> str:
        """Compile comprehensive cinematography prompt."""
        components = []
        if character_bible_text:
            components.append(character_bible_text)
        components.append(f"Action: {self.action}")
        if scene_context:
            components.append(scene_context)
        components.append(f"Camera: {self.camera}, {self.lens}, {self.movement}, {self.composition}")
        components.append(f"Lighting & Color: {self.lighting}, {self.color}")
        return ". ".join(c for c in components if c)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["classification"] = self.classification.value
        return d

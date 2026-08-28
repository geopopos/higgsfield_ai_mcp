"""
Scene Bible & Domain Models for AI MV Director
Defines immutable scenes, environmental rules, lighting, color palettes, continuity constraints, and shot inheritance.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from .ids import generate_scene_id


@dataclass(frozen=True)
class SceneRecord:
    scene_id: str
    project_id: str
    scene_index: int
    title: str
    location: str
    time_of_day: str
    weather: str
    lighting: str
    color_palette: str
    atmosphere: str
    characters: List[str] = field(default_factory=list)
    props: List[str] = field(default_factory=list)
    continuity_constraints: List[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        project_id: str,
        scene_index: int,
        title: str,
        location: str,
        time_of_day: str = "day",
        weather: str = "clear",
        lighting: str = "natural",
        color_palette: str = "cinematic natural",
        atmosphere: str = "",
        characters: Optional[List[str]] = None,
        props: Optional[List[str]] = None,
        continuity_constraints: Optional[List[str]] = None,
    ) -> SceneRecord:
        scene_id = generate_scene_id(project_id, scene_index, title)
        return cls(
            scene_id=scene_id,
            project_id=project_id,
            scene_index=scene_index,
            title=title,
            location=location,
            time_of_day=time_of_day,
            weather=weather,
            lighting=lighting,
            color_palette=color_palette,
            atmosphere=atmosphere,
            characters=characters or [],
            props=props or [],
            continuity_constraints=continuity_constraints or [],
        )

    def compile_scene_context(self) -> str:
        """Compile scene environmental baseline."""
        parts = [
            f"Location: {self.location}",
            f"Time: {self.time_of_day}",
            f"Weather: {self.weather}",
            f"Lighting: {self.lighting}",
            f"Palette: {self.color_palette}",
        ]
        if self.atmosphere:
            parts.append(f"Mood: {self.atmosphere}")
        return ", ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SceneBible:
    """Registry and inheritance engine for project scenes."""

    def __init__(self, scenes: Optional[List[SceneRecord]] = None):
        self._scenes: Dict[str, SceneRecord] = {}
        if scenes:
            for s in scenes:
                self.register(s)

    def register(self, scene: SceneRecord) -> None:
        self._scenes[scene.scene_id] = scene

    def get(self, scene_id: str) -> Optional[SceneRecord]:
        return self._scenes.get(scene_id)

    def list_all(self) -> List[SceneRecord]:
        return sorted(list(self._scenes.values()), key=lambda s: s.scene_index)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenes": [s.to_dict() for s in self.list_all()]
        }

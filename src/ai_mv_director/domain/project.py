"""
Unified Director Domain Model for AI MV Director Platform
Encapsulates Project, Music, Story, Locations, Props, Visual Bible, Scene Bible, Character Bible, Shot List, Timeline, Takes, QA, and Cost.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from .ids import generate_project_id, generate_location_id
from .character import CharacterBible, CharacterRecord
from .scene import SceneBible, SceneRecord


@dataclass(frozen=True)
class LocationRecord:
    location_id: str
    name: str
    description: str
    visual_cues: str
    references: List[str] = field(default_factory=list)

    @classmethod
    def create(cls, name: str, description: str, visual_cues: str = "", references: Optional[List[str]] = None) -> LocationRecord:
        return cls(
            location_id=generate_location_id(name),
            name=name,
            description=description,
            visual_cues=visual_cues,
            references=references or [],
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PropRecord:
    prop_id: str
    name: str
    description: str
    significance: str
    visual_references: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VisualBible:
    aspect_ratio: str = "16:9"
    master_style: str = "Cinematic 35mm film"
    color_grading: str = "Kodak Vision3, rich contrast, soft golden highlights"
    lens_package: str = "Anamorphic / Prime lenses"
    negative_prompt: str = "cgi look, distorted face, low quality, artifacting, blur"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MusicSpec:
    title: str
    artist: str = ""
    audio_path: Optional[str] = None
    bpm: float = 120.0
    key: str = "C Major"
    total_duration_sec: float = 240.0
    lyrics: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StorySpec:
    logline: str
    synopsis: str
    emotional_arc: str
    acts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Project:
    """The canonical project root entity."""
    project_id: str
    title: str
    story: StorySpec
    music: MusicSpec
    visual_bible: VisualBible
    character_bible: CharacterBible
    scene_bible: SceneBible
    locations: Dict[str, LocationRecord] = field(default_factory=dict)
    props: Dict[str, PropRecord] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        title: str,
        story_text: str,
        music_title: Optional[str] = None,
        bpm: float = 120.0,
        total_duration_sec: float = 240.0,
        aspect_ratio: str = "16:9",
    ) -> Project:
        proj_id = generate_project_id(title, story_text)
        story = StorySpec(
            logline=story_text.split(".")[0] if "." in story_text else story_text[:60],
            synopsis=story_text,
            emotional_arc="Ascending Emotional Catharsis",
        )
        music = MusicSpec(
            title=music_title or title,
            bpm=bpm,
            total_duration_sec=total_duration_sec,
        )
        return cls(
            project_id=proj_id,
            title=title,
            story=story,
            music=music,
            visual_bible=VisualBible(aspect_ratio=aspect_ratio),
            character_bible=CharacterBible(),
            scene_bible=SceneBible(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "title": self.title,
            "story": self.story.to_dict(),
            "music": self.music.to_dict(),
            "visual_bible": self.visual_bible.to_dict(),
            "character_bible": self.character_bible.to_dict(),
            "scene_bible": self.scene_bible.to_dict(),
            "locations": {k: v.to_dict() for k, v in self.locations.items()},
            "props": {k: v.to_dict() for k, v in self.props.items()},
            "metadata": self.metadata,
        }

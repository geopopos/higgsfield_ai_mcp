"""
Domain models for AI MV Director Platform
"""

from .ids import (
    generate_deterministic_id,
    generate_unique_id,
    generate_project_id,
    generate_character_id,
    generate_location_id,
    generate_scene_id,
    generate_shot_id,
    generate_take_id,
    generate_asset_id,
    generate_timeline_id,
    generate_job_id,
)
from .character import CharacterRecord, CharacterBible
from .scene import SceneRecord, SceneBible
from .project import (
    LocationRecord,
    PropRecord,
    VisualBible,
    MusicSpec,
    StorySpec,
    Project,
)

__all__ = [
    "generate_deterministic_id",
    "generate_unique_id",
    "generate_project_id",
    "generate_character_id",
    "generate_location_id",
    "generate_scene_id",
    "generate_shot_id",
    "generate_take_id",
    "generate_asset_id",
    "generate_timeline_id",
    "generate_job_id",
    "CharacterRecord",
    "CharacterBible",
    "SceneRecord",
    "SceneBible",
    "LocationRecord",
    "PropRecord",
    "VisualBible",
    "MusicSpec",
    "StorySpec",
    "Project",
]

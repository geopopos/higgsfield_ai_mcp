"""
Immutable Entity ID Utilities for AI MV Director Domain
Ensures deterministic and unique IDs across all project assets and entities.
"""

import hashlib
import uuid
from typing import Optional


def generate_deterministic_id(prefix: str, *content_parts: str) -> str:
    """Generate a deterministic ID from content parts."""
    raw = "|".join(str(p).strip() for p in content_parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def generate_unique_id(prefix: str) -> str:
    """Generate a unique random ID with prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def generate_project_id(title: str, story: str) -> str:
    return generate_deterministic_id("proj", title, story)


def generate_character_id(name: str) -> str:
    return generate_deterministic_id("char", name.lower())


def generate_location_id(name: str) -> str:
    return generate_deterministic_id("loc", name.lower())


def generate_scene_id(project_id: str, scene_index: int, scene_title: str) -> str:
    return generate_deterministic_id("scn", project_id, str(scene_index), scene_title)


def generate_shot_id(scene_id: str, shot_index: int, action: str) -> str:
    return generate_deterministic_id("shot", scene_id, str(shot_index), action[:30])


def generate_take_id(shot_id: str, attempt: int) -> str:
    return generate_deterministic_id("take", shot_id, str(attempt), uuid.uuid4().hex[:6])


def generate_asset_id(sha256_hash: str) -> str:
    return f"asset_{sha256_hash[:12]}"


def generate_timeline_id(project_id: str, version: int = 1) -> str:
    return generate_deterministic_id("timeline", project_id, str(version))


def generate_job_id(shot_id: str) -> str:
    return generate_deterministic_id("job", shot_id, uuid.uuid4().hex[:6])

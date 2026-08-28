#!/usr/bin/env python3
"""
CapCut / JianYing Draft MCP Server for Auto-MV Pipeline.
Generates draft_content.json and exports project drafts directly into CapCut's draft folder.
"""

import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

mcp = FastMCP("capcut-draft-mcp")


def get_capcut_draft_dir() -> Path:
    """Locate local CapCut / JianYing User Draft Directory."""
    user_home = Path.home()
    possible_paths = [
        user_home / "AppData/Local/CapCut/User Data/Projects/com.lveditor.draft",
        user_home / "AppData/Local/JianyingPro/User Data/Projects/com.lveditor.draft",
    ]
    for p in possible_paths:
        if p.exists():
            return p
    default_dir = user_home / "AppData/Local/CapCut/User Data/Projects/com.lveditor.draft"
    default_dir.mkdir(parents=True, exist_ok=True)
    return default_dir


@mcp.tool()
def create_capcut_draft(
    project_name: str,
    video_clips: List[str],
    audio_file: str,
    fps: int = 24,
) -> Dict[str, Any]:
    """
    Generate a CapCut draft project folder containing draft_content.json snapped to video clips & audio.
    """
    draft_base = get_capcut_draft_dir()
    project_id = str(uuid.uuid4()).upper()
    project_folder = draft_base / f"{project_name}_{project_id[:8]}"
    project_folder.mkdir(parents=True, exist_ok=True)

    # Basic CapCut draft JSON schema template
    draft_content = {
        "canvas_config": {"height": 1080, "ratio": "16:9", "width": 1920},
        "color_space": 0,
        "config": {"adjust_max_index": 1, "extract_audio_index": 0},
        "fps": fps,
        "id": project_id,
        "materials": {
            "audios": [{"id": str(uuid.uuid4()), "path": os.path.abspath(audio_file)}],
            "videos": [
                {"id": str(uuid.uuid4()), "path": os.path.abspath(clip)}
                for clip in video_clips
            ],
        },
        "tracks": [
            {"id": str(uuid.uuid4()), "type": "video", "segments": []},
            {"id": str(uuid.uuid4()), "type": "audio", "segments": []},
        ],
        "version": 6,
    }

    draft_file = project_folder / "draft_content.json"
    with open(draft_file, "w", encoding="utf-8") as f:
        json.dump(draft_content, f, ensure_ascii=False, indent=2)

    return {
        "status": "success",
        "project_name": project_name,
        "draft_path": str(draft_file.resolve()),
        "capcut_folder": str(project_folder.resolve()),
    }


def main():
    mcp.run()


if __name__ == "__main__":
    main()

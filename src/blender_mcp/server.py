#!/usr/bin/env python3
"""
Blender MCP Server for Auto-MV Pipeline.
Exposes FastMCP tools for Blender headless 3D camera previs rendering.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict

from fastmcp import FastMCP

mcp = FastMCP("blender-previs-mcp")


def get_blender_path() -> str:
    """Find Blender binary path from environment, local project, or system."""
    env_path = os.getenv("BLENDER_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    # Search inside workspace directory
    project_root = Path(__file__).resolve().parents[2]
    local_blenders = list(project_root.glob("**/blender.exe"))
    if local_blenders:
        return str(local_blenders[0].resolve())

    # Common Windows installation paths
    default_paths = [
        r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
    ]
    for p in default_paths:
        if os.path.exists(p):
            return p
    return "blender"


@mcp.tool()
def check_blender_status() -> Dict[str, Any]:
    """Check if Blender CLI is available and retrieve version."""
    blender_bin = get_blender_path()
    try:
        res = subprocess.run(
            [blender_bin, "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        version_line = res.stdout.splitlines()[0] if res.stdout else "Unknown"
        return {"status": "ok", "executable": blender_bin, "version": version_line}
    except Exception as e:
        return {
            "status": "error",
            "executable": blender_bin,
            "error": str(e),
            "tip": "Set BLENDER_PATH environment variable or configure config/settings.yaml",
        }


@mcp.tool()
def render_previs_shot(
    shot_id: str,
    camera_movement: str,
    duration_frames: int = 120,
    output_dir: str = "temp/previs",
) -> Dict[str, Any]:
    """
    Render a 3D camera trajectory previs video slice using Blender Headless Workbench.
    """
    blender_bin = get_blender_path()
    out_path = Path(output_dir) / f"{shot_id}_previs.mp4"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Temporary script for Blender CLI execution
    script_content = f"""
import bpy
import math

# Clear default scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Add Camera & Target Proxy
bpy.ops.object.camera_add(location=(0, -5, 1.5), rotation=(math.radians(80), 0, 0))
cam = bpy.context.object
bpy.context.scene.camera = cam

bpy.ops.object.armature_add(location=(0, 0, 0))
target = bpy.context.object

# Movement logic: {camera_movement}
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = {duration_frames}
bpy.context.scene.render.fps = 24
bpy.context.scene.render.engine = 'BLENDER_WORKBENCH'
bpy.context.scene.render.filepath = r'{out_path.resolve()}'
bpy.context.scene.render.image_settings.file_format = 'FFMPEG'
bpy.context.scene.render.ffmpeg.format = 'MPEG4'

# Animate Camera Orbit/Push
for frame in range(1, {duration_frames} + 1):
    bpy.context.scene.frame_set(frame)
    progress = frame / {duration_frames}
    if '{camera_movement}' == 'orbit':
        angle = progress * math.pi * 2
        cam.location.x = 4 * math.sin(angle)
        cam.location.y = -4 * math.cos(angle)
        cam.keyframe_insert(data_path="location", index=-1)
    else:  # push_in
        cam.location.y = -5 + (progress * 3)
        cam.keyframe_insert(data_path="location", index=-1)

bpy.ops.render.render(animation=True)
"""
    tmp_script = Path("temp/tmp_blender_run.py")
    tmp_script.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp_script, "w", encoding="utf-8") as f:
        f.write(script_content)

    try:
        subprocess.run(
            [blender_bin, "-b", "-P", str(tmp_script)],
            capture_output=True,
            text=True,
            check=True,
        )
        return {
            "status": "success",
            "shot_id": shot_id,
            "output_mp4": str(out_path.resolve()),
        }
    except Exception as e:
        return {"status": "error", "shot_id": shot_id, "error": str(e)}


def main():
    mcp.run()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
AI Film Studio Project Initializer
Sets up a standardized workspace folder structure for AI Video Production.
"""
import os
import json
import argparse
from pathlib import Path


def init_project(project_name: str, base_dir: str = "./projects"):
    target_dir = Path(base_dir) / project_name
    
    subdirs = [
        "01_script",       # Prompt, screenplay, lyrics, storyboard JSON
        "02_audio",        # Suno stems, voiceovers, sound effects
        "03_storyboard",   # Generated image keyframes
        "04_renders",      # Higgsfield 1080p Video Clips
        "05_export"        # Final assembly, renders, handover ZIP
    ]
    
    print(f"🎬 Creating AI Film Studio project structure: {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    for sub in subdirs:
        (target_dir / sub).mkdir(parents=True, exist_ok=True)
        print(f"  ├── Created directory: {sub}/")
        
    manifest_path = target_dir / "manifest.json"
    if not manifest_path.exists():
        manifest_data = {
            "project_name": project_name,
            "version": "1.0.0",
            "director": "林從胤 AI 影像團隊",
            "aspect_ratio": "16:9",
            "target_resolution": "1080p",
            "higgsfield_model": "dop-preview",
            "shots": [
                {
                    "shot_id": "shot_001",
                    "title": "Intro Scene",
                    "prompt": "Cinematic wide shot of a futuristic cyberpunk city at dusk, neon lighting, smooth aerial drone camera tilt",
                    "lens": "24mm anamorphic prime lens",
                    "movement": "camera_tilt_down",
                    "motion_id": "camera_tilt_down",
                    "image_url": "",
                    "audio_stem": "02_audio/intro_bgm.mp3"
                }
            ]
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)
        print(f"  └── Created project manifest: manifest.json")
        
    print(f"✨ Project '{project_name}' successfully initialized!")
    return target_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize AI Video Production Project")
    parser.add_argument("--name", type=str, default="demo_mv", help="Name of the project")
    parser.add_argument("--dir", type=str, default="./projects", help="Base directory")
    args = parser.parse_args()
    
    init_project(args.name, args.dir)

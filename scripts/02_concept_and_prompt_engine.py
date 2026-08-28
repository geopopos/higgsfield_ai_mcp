#!/usr/bin/env python3
"""
02_concept_and_prompt_engine.py - Storyboard & Prompt Architect Engine

Reads `beats_manifest.json` from Step 1, analyzes music sections & lyrics,
and generates `shots_manifest.json` and `assets_manifest.json`.

Usage:
    python scripts/02_concept_and_prompt_engine.py --beats output/beats_manifest.json
    python scripts/02_concept_and_prompt_engine.py --dry-run
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


class ConceptPromptEngine:
    """Storyboard architect and prompt compiler."""

    def __init__(self, style_preset: str = "cyberpunk_cinematic"):
        self.style_preset = style_preset

    def generate_storyboard(
        self, beats_manifest: Dict[str, Any], lyrics_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compile shot matrix and visual asset requirements based on audio analysis."""
        bpm = beats_manifest.get("bpm", 120.0)
        fps = beats_manifest.get("fps", 24)
        duration = beats_manifest.get("duration_sec", 60.0)
        sections = beats_manifest.get("energy_sections", [])
        beats = beats_manifest.get("beats", [])
        lyrics = beats_manifest.get("lyrics_timeline", [])

        # Load exact lyrics file if provided
        exact_lyrics_map = {}
        if lyrics_file and os.path.exists(lyrics_file):
            with open(lyrics_file, "r", encoding="utf-8") as lf:
                raw_text = lf.read()
            # Parse sections like [Intro...], [Verse 1...], etc.
            import re
            sec_blocks = re.split(r'\[([^\]]+)\]', raw_text)
            current_tag = "General"
            for i in range(1, len(sec_blocks), 2):
                tag = sec_blocks[i].strip()
                content = sec_blocks[i+1].strip().splitlines()
                clean_lines = [l.strip() for l in content if l.strip() and not l.startswith('//')]
        shots = []
        shot_counter = 1

        # Process each energy section to map into camera shots
        for sec_idx, sec in enumerate(sections):
            start_t = sec["start"]
            end_t = sec["end"]
            energy_label = sec["label"]

            # Higher energy = shorter shot duration (faster cuts)
            if "Drop" in energy_label or sec["energy"] > 0.7:
                shot_duration = 3.0
                movement = "fast_zoom_drop"
                lens = "wide_24mm"
            elif "Chorus" in energy_label or sec["energy"] > 0.4:
                shot_duration = 4.0
                movement = "orbit_3d"
                lens = "portrait_85mm"
            else:
                shot_duration = 6.0
                movement = "slow_push_in"
                lens = "cinematic_35mm"

            t = start_t
            sec_shot_idx = 0
            while t < end_t:
                shot_end = min(t + shot_duration, end_t)
                start_frame = int(round(t * fps))
                end_frame = int(round(shot_end * fps))

                # Match lyric line from exact lyrics or whisper timeline
                matching_lyric = ""
                # Priority 1: Check exact parsed lyrics by section
                matched_sec_lines = []
                for k, lines in exact_lyrics_map.items():
                    if any(w in k for w in energy_label.lower().split()[:2]):
                        matched_sec_lines = lines
                        break
                if matched_sec_lines and sec_shot_idx < len(matched_sec_lines):
                    matching_lyric = matched_sec_lines[sec_shot_idx]
                elif matched_sec_lines:
                    matching_lyric = matched_sec_lines[-1]
                else:
                    # Fallback to Whisper timeline
                    for lyr in lyrics:
                        if lyr["start"] <= t <= lyr["end"]:
                            matching_lyric = lyr["text"]
                            break

                shot_entry = {
                    "shot_id": f"shot_{shot_counter:03d}",
                    "section": sec["section_index"],
                    "start_time": float(round(t, 2)),
                    "end_time": float(round(shot_end, 2)),
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                    "duration_sec": float(round(shot_end - t, 2)),
                    "camera": {
                        "lens": lens,
                        "movement": movement,
                    },
                    "prompt": (
                        f"Cinematic 8K MV shot, {self.style_preset} style, "
                        f"character performing in dramatic lighting, {movement} camera angle, "
                        f"photorealistic, 35mm film grain, dynamic mood. Lyric theme: '{matching_lyric}'"
                    ),
                    "character_ref": "character_main_sheet.png",
                    "location_ref": f"location_sec_{sec_idx + 1}.png",
                }
                shots.append(shot_entry)
                shot_counter += 1
                sec_shot_idx += 1
                t = shot_end

        shots_manifest = {
            "style_preset": self.style_preset,
            "total_shots": len(shots),
            "bpm": bpm,
            "fps": fps,
            "duration_sec": duration,
            "shots": shots,
        }

        assets_manifest = {
            "characters": [
                {
                    "id": "character_main",
                    "name": "Main Singer / Protagonist",
                    "prompt": f"Character concept sheet, 4-view turnaround (front, side, 3/4, back), {self.style_preset} aesthetic, futuristic outfit, highly detailed, 8k",
                    "output_filename": "character_main_sheet.png",
                }
            ],
            "locations": [
                {
                    "id": f"location_sec_{i + 1}",
                    "name": f"Environment for Section {i + 1}",
                    "prompt": f"Cinematic location keyframe, {self.style_preset} environment, wide angle atmospheric lighting, volumetric fog, 8k",
                    "output_filename": f"location_sec_{i + 1}.png",
                }
                for i in range(len(sections))
            ],
        }

        return {"shots_manifest": shots_manifest, "assets_manifest": assets_manifest}


def main():
    parser = argparse.ArgumentParser(description="Auto-MV Pipeline Step 2: Storyboard & Prompt Engine")
    parser.add_argument("--beats", help="Path to beats_manifest.json")
    parser.add_argument("--lyrics", help="Path to exact lyrics text file", default=None)
    parser.add_argument("--output-shots", default="shots_manifest.json", help="Output path for shots_manifest.json")
    parser.add_argument("--output-assets", default="assets_manifest.json", help="Output path for assets_manifest.json")
    parser.add_argument("--style", default="korean_dark_trap_uk_drill_cyberpunk", help="Visual style preset")
    parser.add_argument("--dry-run", action="store_true", help="Generate mock data")
    args = parser.parse_args()

    if args.dry_run or not args.beats or not os.path.exists(args.beats):
        print("[*] Running in dry-run / mock mode...")
        beats_data = {
            "bpm": 140.0,
            "fps": 24,
            "duration_sec": 60.0,
            "energy_sections": [
                {"section_index": 1, "start": 0.0, "end": 15.0, "energy": 0.2, "label": "Intro"},
                {"section_index": 2, "start": 15.0, "end": 30.0, "energy": 0.6, "label": "Verse 1"},
                {"section_index": 3, "start": 30.0, "end": 45.0, "energy": 0.8, "label": "Chorus"},
                {"section_index": 4, "start": 45.0, "end": 60.0, "energy": 0.3, "label": "Outro"},
            ],
            "beats": [],
            "lyrics_timeline": [],
        }
    else:
        with open(args.beats, "r", encoding="utf-8") as f:
            beats_data = json.load(f)

    engine = ConceptPromptEngine(style_preset=args.style)
    result = engine.generate_storyboard(beats_data, lyrics_file=args.lyrics)

    out_shots = Path(args.output_shots)
    out_shots.parent.mkdir(parents=True, exist_ok=True)
    with open(out_shots, "w", encoding="utf-8") as f:
        json.dump(result["shots_manifest"], f, ensure_ascii=False, indent=2)

    out_assets = Path(args.output_assets)
    out_assets.parent.mkdir(parents=True, exist_ok=True)
    with open(out_assets, "w", encoding="utf-8") as f:
        json.dump(result["assets_manifest"], f, ensure_ascii=False, indent=2)

    print(f"[SUCCESS] Storyboard compiled: {out_shots.resolve()}")
    print(f"[SUCCESS] Assets manifest compiled: {out_assets.resolve()}")

    # Generate human-readable versions
    generate_readable_markdowns(result["shots_manifest"], result["assets_manifest"], out_shots, out_assets)

    # Generate interactive HTML dashboard
    try:
        from generate_html_dashboard import generate_dashboard
        proj_dir = out_shots.parent
        generate_dashboard(str(proj_dir))
    except Exception as e:
        print(f"[!] HTML Dashboard auto-generation notice: {e}")


def generate_readable_markdowns(shots_manifest: dict, assets_manifest: dict, out_shots_path: Path, out_assets_path: Path):
    # Generate shots markdown
    md_shots_path = out_shots_path.with_name(out_shots_path.stem + "_readable.md")
    
    md_shots = []
    md_shots.append("# 🎬 鏡頭設計與時間軸報告 (Storyboard Timeline Report)\n")
    md_shots.append(f"- **專案視覺風格 (Style Preset)**: `{shots_manifest.get('style_preset', 'N/A')}`")
    md_shots.append(f"- **總鏡頭數 (Total Shots)**: `{shots_manifest.get('total_shots', 0)}`")
    md_shots.append(f"- **BPM**: `{shots_manifest.get('bpm', 0.0)}`")
    md_shots.append(f"- **FPS**: `{shots_manifest.get('fps', 24)}`")
    md_shots.append(f"- **總時長 (Duration)**: `{shots_manifest.get('duration_sec', 0.0)} 秒`\n")
    
    md_shots.append("## 📹 鏡頭明細表 (Shot Detail Matrix)\n")
    md_shots.append("| 鏡頭 ID (Shot ID) | 時間 (Time) | 訊框區間 (Frames) | 長度 (Duration) | 相機設定 (Camera) | 歌詞與情境 (Lyric Theme) | 畫面描述提示詞 (Visual Prompt) |")
    md_shots.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    for shot in shots_manifest.get("shots", []):
        shot_id = shot.get("shot_id", "N/A")
        start_t = shot.get("start_time", 0.0)
        end_t = shot.get("end_time", 0.0)
        start_f = shot.get("start_frame", 0)
        end_f = shot.get("end_frame", 0)
        dur = shot.get("duration_sec", 0.0)
        
        cam = shot.get("camera", {})
        camera_str = f"鏡頭: {cam.get('lens', 'default')}<br>運鏡: {cam.get('movement', 'default')}"
        
        prompt = shot.get("prompt", "")
        # Extract lyric theme if exists
        lyric_theme = ""
        if "Lyric theme:" in prompt:
            parts = prompt.split("Lyric theme:")
            prompt_str = parts[0].strip()
            lyric_theme = parts[1].strip().strip("'\"")
        else:
            prompt_str = prompt
            
        md_shots.append(f"| `{shot_id}` | {start_t}s - {end_t}s | {start_f} - {end_f} | {dur}s | {camera_str} | **{lyric_theme}** | {prompt_str} |")
        
    with open(md_shots_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_shots))
    print(f"[SUCCESS] Human-readable storyboard generated: {md_shots_path.resolve()}")

    # Generate assets markdown
    md_assets_path = out_assets_path.with_name(out_assets_path.stem + "_readable.md")
    
    md_assets = []
    md_assets.append("# 🎭 視覺資產生成清單 (Visual Asset Generation Manifest)\n")
    
    md_assets.append("## 👤 角色設計需求 (Characters)")
    for char in assets_manifest.get("characters", []):
        md_assets.append(f"### ➔ 角色 ID: `{char.get('id')}` ({char.get('name')})")
        md_assets.append(f"- **輸出檔名 (Output File)**: `{char.get('output_filename')}`")
        md_assets.append(f"- **生圖提示詞 (Generation Prompt)**:\n  > {char.get('prompt')}\n")
        
    md_assets.append("## 📍 場景位置需求 (Locations)")
    md_assets.append("| 場景 ID (Location ID) | 名稱 (Name) | 輸出檔名 (Output File) | 場景描述提示詞 (Location Prompt) |")
    md_assets.append("| :--- | :--- | :--- | :--- |")
    for loc in assets_manifest.get("locations", []):
        md_assets.append(f"| `{loc.get('id')}` | {loc.get('name')} | `{loc.get('output_filename')}` | {loc.get('prompt')} |")
        
    with open(md_assets_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_assets))
    print(f"[SUCCESS] Human-readable assets manifest generated: {md_assets_path.resolve()}")


if __name__ == "__main__":
    main()

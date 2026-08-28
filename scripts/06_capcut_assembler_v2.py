#!/usr/bin/env python3
"""
CapCut Draft Assembler v2 — Schema-Clone Strategy
===================================================
Instead of building draft_content.json from scratch (which CapCut rejects),
this script:
  1. Reads a REAL CapCut draft_content.json as the "template" (donor schema).
  2. Strips its materials and tracks.
  3. Injects our beat-snapped timeline (audio + video segments).
  4. Writes the result to the target CapCut project folder.

This preserves every undocumented field CapCut validates internally.
"""

import argparse, json, uuid, os, sys
from pathlib import Path

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def gen_id():
    return str(uuid.uuid4())

def gen_upper_id():
    return str(uuid.uuid4()).upper()

def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"[SUCCESS] Wrote {p}  ({os.path.getsize(p):,} bytes)")

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="CapCut Draft Assembler v2 (schema-clone)")
    ap.add_argument("--template-dir", required=True,
                    help="Path to a REAL working CapCut project folder (donor)")
    ap.add_argument("--beats", required=True, help="beats_manifest.json")
    ap.add_argument("--shots", required=True, help="shots_manifest.json")
    ap.add_argument("--renders-dir", required=True)
    ap.add_argument("--audio-dir", required=True)
    ap.add_argument("--output-dir", required=True,
                    help="Target CapCut project folder")
    args = ap.parse_args()

    template_dir = Path(args.template_dir)
    out_dir = Path(args.output_dir)
    renders_dir = Path(args.renders_dir).resolve()
    audio_dir = Path(args.audio_dir).resolve()

    # ── 1. Load template ───────────────────────────────────────────────
    template_path = template_dir / "draft_content.json"
    if not template_path.exists():
        sys.exit(f"[FATAL] Template draft_content.json not found: {template_path}")

    draft = load_json(template_path)
    print(f"[*] Loaded template from {template_path}  (keys: {len(draft)})")

    # ── 2. Preserve target project's internal ID ───────────────────────
    target_content = out_dir / "draft_content.json"
    if target_content.exists():
        try:
            existing = load_json(target_content)
            draft["id"] = existing["id"]
            print(f"[*] Preserved target project ID: {draft['id']}")
        except Exception:
            pass

    # ── 3. Load our manifests ──────────────────────────────────────────
    beats = load_json(args.beats)
    shots = load_json(args.shots)

    # Collect render files (sorted)
    render_files = sorted(renders_dir.glob("shot_*_render.mp4"))
    if not render_files:
        sys.exit(f"[FATAL] No render files found in {renders_dir}")
    print(f"[*] Found {len(render_files)} render files")

    # Find audio file
    audio_files = list(audio_dir.glob("*.wav")) + list(audio_dir.glob("*.mp3"))
    if not audio_files:
        sys.exit(f"[FATAL] No audio files in {audio_dir}")
    audio_file = audio_files[0]
    print(f"[*] Audio: {audio_file.name}")

    # ── 4. Build materials ─────────────────────────────────────────────
    # Keep all the empty sub-arrays from template but replace audios/videos
    audio_id = gen_id()
    video_ids = [gen_id() for _ in render_files]

    # Build audio material entry — minimal but with all fields CapCut needs
    audio_material = {
        "ai_music_generate_scene": 0,
        "ai_music_type": 0,
        "aigc_history_id": "",
        "aigc_item_id": "",
        "app_id": 0,
        "category_id": "",
        "category_name": "local",
        "check_flag": 1,
        "cloned_model_type": "",
        "copyright_limit_type": "none",
        "duration": 0,  # will be set later
        "effect_id": "",
        "formula_id": "",
        "id": audio_id,
        "intensifies_path": "",
        "is_ai_clone_tone": False,
        "is_ai_clone_tone_post": False,
        "is_text_edit_overdub": False,
        "is_ugc": False,
        "local_material_id": gen_id(),
        "lyric_type": 0,
        "mock_tone_speaker": "",
        "moyin_emotion": "",
        "music_id": gen_id(),
        "music_source": "",
        "name": audio_file.name,
        "path": str(audio_file).replace("\\", "/"),
        "pgc_id": "",
        "pgc_name": "",
        "query": "",
        "request_id": "",
        "resource_id": "",
        "search_id": "",
        "similiar_music_info": {"original_song_id": "", "original_song_name": ""},
        "sound_separate_type": "",
        "source_from": "",
        "source_platform": 0,
        "team_id": "",
        "text_id": "",
        "third_resource_id": "",
        "tone_category_id": "",
        "tone_category_name": "",
        "tone_effect_id": "",
        "tone_effect_name": "",
        "tone_emotion_name_key": "",
        "tone_emotion_role": "",
        "tone_emotion_scale": 0.0,
        "tone_emotion_selection": "",
        "tone_emotion_style": "",
        "tone_platform": "",
        "tone_second_category_id": "",
        "tone_second_category_name": "",
        "tone_speaker": "",
        "tone_type": "",
        "tts_generate_scene": "",
        "tts_task_id": "",
        "type": "extract_music",
        "video_id": "",
        "wave_points": []
    }

    # Build video material entries
    video_materials = []
    for i, (rf, vid) in enumerate(zip(render_files, video_ids)):
        video_materials.append({
            "aigc_type": "none",
            "audio_fade": None,
            "cartoon_path": "",
            "category_id": "",
            "category_name": "local",
            "check_flag": 1,
            "crop": {
                "lower_left_x": 0.0, "lower_left_y": 1.0,
                "lower_right_x": 1.0, "lower_right_y": 1.0,
                "upper_left_x": 0.0, "upper_left_y": 0.0,
                "upper_right_x": 1.0, "upper_right_y": 0.0
            },
            "crop_ratio": "free",
            "crop_scale": 1.0,
            "duration": 1000000,  # placeholder, CapCut recalculates
            "extra_type_option": 0,
            "formula_id": "",
            "freeze": None,
            "gameplay_album_path": "",
            "has_audio": False,
            "height": 1080,
            "id": vid,
            "intensifies_audio_path": "",
            "intensifies_path": "",
            "is_ai_generate_content": False,
            "is_copyright": False,
            "is_text_edit_overdub": False,
            "is_unified_beauty_mode": False,
            "local_id": "",
            "local_material_id": gen_id(),
            "material_id": "",
            "material_name": rf.name,
            "material_url": "",
            "matting": {"flag": 0, "has_use_quick_brush": False, "has_use_quick_eraser": False,
                        "interactiveTime": [], "path": "", "strokes": []},
            "media_path": "",
            "music_id": gen_id(),
            "object_locked": None,
            "origin_material_id": "",
            "path": str(rf.resolve()).replace("\\", "/"),
            "picture_from": "none",
            "picture_set_category_id": "",
            "picture_set_category_name": "",
            "request_id": "",
            "reverse_path": "",
            "smart_motion": None,
            "source": 0,
            "source_platform": 0,
            "stable": {"matrix_path": "", "stable_level": 0, "time_range": {"duration": 0, "start": 0}},
            "team_id": "",
            "type": "video",
            "video_algorithm": {
                "algorithms": [],
                "deflicker": None,
                "motion_blur_config": None,
                "noise_reduction": None,
                "path": "",
                "quality_enhance": None
            },
            "width": 1920
        })

    # Replace materials — keep all existing empty sub-arrays from template
    if "materials" not in draft:
        draft["materials"] = {}

    mat = draft["materials"]
    # Set our audio + video, keep everything else as empty arrays
    mat["audios"] = [audio_material]
    mat["videos"] = video_materials

    # Ensure all standard material sub-arrays exist (empty)
    for key in [
        "ai_translates", "audio_balances", "audio_effects", "audio_fades",
        "audio_pannings", "audio_pitch_shifts", "audio_track_indexes",
        "beats", "canvases", "chromas", "color_curves", "common_mask",
        "digital_human_model_dressing", "digital_humans", "drafts",
        "effects", "flowers", "green_screens", "handwrites",
        "hsl", "images", "log_color_wheels", "loudnesses",
        "manual_deformations", "masks", "material_animations",
        "material_colors", "multi_language_refs", "placeholders",
        "plugin_list", "primary_color_wheels", "realtime_denoises",
        "smart_crops", "smart_relights", "sound_channel_mappings",
        "speeds", "stickers", "tail_leaders", "text_templates",
        "texts", "time_marks", "transitions", "video_effects",
        "video_trackings", "vocal_beautifys", "vocal_separations"
    ]:
        if key not in mat:
            mat[key] = []

    # ── 5. Build tracks (audio + video with beat-snapped segments) ─────
    beat_times = beats.get("beats", [])
    shot_list = shots.get("shots", [])

    # Calculate total duration in CapCut microseconds (1s = 1,000,000)
    # Use beat times if available, otherwise use shots
    total_duration_us = 0

    video_segments = []
    for i, rf in enumerate(render_files):
        vid = video_ids[i]

        # Determine timing from beats or shots
        if i < len(shot_list):
            shot = shot_list[i]
            start_s = shot.get("start_time", i * 5.0)
            dur_s = shot.get("duration", 5.0)
        elif i < len(beat_times) - 1:
            start_s = beat_times[i]
            dur_s = beat_times[i + 1] - beat_times[i]
        else:
            start_s = i * 5.0
            dur_s = 5.0

        start_us = int(start_s * 1_000_000)
        dur_us = int(dur_s * 1_000_000)
        end_us = start_us + dur_us
        if end_us > total_duration_us:
            total_duration_us = end_us

        video_segments.append({
            "cartoon": False,
            "clip": {"alpha": 1.0, "flip": {"horizontal": False, "vertical": False},
                     "rotation": 0.0, "scale": {"x": 1.0, "y": 1.0},
                     "transform": {"x": 0.0, "y": 0.0}},
            "common_keyframes": [],
            "enable_adjust": True,
            "enable_color_correct_adjust": False,
            "enable_color_curves": True,
            "enable_color_match_adjust": False,
            "enable_color_wheels": True,
            "enable_lut": True,
            "enable_smart_color_adjust": False,
            "extra_material_refs": [],
            "group_id": "",
            "hdr_settings": {"environment": 1, "gallery_tone_mapping": 0},
            "id": gen_id(),
            "intensifies_audio": False,
            "is_placeholder": False,
            "is_tone_modify": False,
            "keyframe_refs": [],
            "last_nonzero_volume": 1.0,
            "material_id": vid,
            "render_index": 0,
            "responsive_layout": {"enable": False, "horizontal_pos_layout": 0,
                                  "size_layout": 0, "target_follow": "",
                                  "vertical_pos_layout": 0},
            "reverse": False,
            "source_timerange": {"duration": dur_us, "start": 0},
            "speed": 1.0,
            "target_timerange": {"duration": dur_us, "start": start_us},
            "template_id": "",
            "template_scene": "default",
            "track_attribute": 0,
            "track_render_index": 0,
            "uniform_scale": {"on": True, "value": 1.0},
            "visible": True,
            "volume": 1.0
        })

    # Audio segment
    audio_material["duration"] = total_duration_us
    audio_segment = {
        "cartoon": False,
        "clip": {"alpha": 1.0, "flip": {"horizontal": False, "vertical": False},
                 "rotation": 0.0, "scale": {"x": 1.0, "y": 1.0},
                 "transform": {"x": 0.0, "y": 0.0}},
        "common_keyframes": [],
        "enable_adjust": False,
        "enable_color_correct_adjust": False,
        "enable_color_curves": True,
        "enable_color_match_adjust": False,
        "enable_color_wheels": True,
        "enable_lut": True,
        "enable_smart_color_adjust": False,
        "extra_material_refs": [],
        "group_id": "",
        "hdr_settings": {"environment": 1, "gallery_tone_mapping": 0},
        "id": gen_id(),
        "intensifies_audio": False,
        "is_placeholder": False,
        "is_tone_modify": False,
        "keyframe_refs": [],
        "last_nonzero_volume": 1.0,
        "material_id": audio_id,
        "render_index": 0,
        "responsive_layout": {"enable": False, "horizontal_pos_layout": 0,
                              "size_layout": 0, "target_follow": "",
                              "vertical_pos_layout": 0},
        "reverse": False,
        "source_timerange": {"duration": total_duration_us, "start": 0},
        "speed": 1.0,
        "target_timerange": {"duration": total_duration_us, "start": 0},
        "template_id": "",
        "template_scene": "default",
        "track_attribute": 0,
        "track_render_index": 0,
        "uniform_scale": {"on": True, "value": 1.0},
        "visible": True,
        "volume": 1.0
    }

    draft["tracks"] = [
        {
            "attribute": 0,
            "flag": 0,
            "id": gen_id(),
            "is_default_name": True,
            "name": "",
            "segments": video_segments,
            "type": "video"
        },
        {
            "attribute": 0,
            "flag": 0,
            "id": gen_id(),
            "is_default_name": True,
            "name": "",
            "segments": [audio_segment],
            "type": "audio"
        }
    ]

    # ── 6. Update top-level fields ─────────────────────────────────────
    draft["duration"] = total_duration_us
    draft["canvas_config"] = {
        "height": 1080,
        "ratio": "16:9",
        "width": 1920,
        "background": None
    }
    draft["fps"] = 24.0

    # ── 7. Write ───────────────────────────────────────────────────────
    out_dir.mkdir(parents=True, exist_ok=True)
    save_json(target_content, draft)
    print(f"[*] Total timeline: {total_duration_us / 1_000_000:.2f}s, "
          f"{len(video_segments)} video segments, 1 audio segment")


if __name__ == "__main__":
    main()

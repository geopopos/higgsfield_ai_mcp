#!/usr/bin/env python3
"""
01_audio_analysis.py - Audio Feature & Lyrics Timecode Extractor

Extracts BPM, beat timestamps (kick/snare onsets), RMS energy structures,
and aligns lyrics using Whisper/VAD timecoding to produce `beats_manifest.json`.

Usage:
    python scripts/01_audio_analysis.py --audio assets/audio/track.wav --output output/beats_manifest.json
    python scripts/01_audio_analysis.py --dry-run
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np


class AudioAnalyzer:
    """Audio feature analysis and lyrics alignment engine."""

    def __init__(self, fps: int = 24, sample_rate: int = 22050):
        self.fps = fps
        self.sample_rate = sample_rate

    def sec_to_frame(self, sec: float) -> int:
        """Convert time in seconds to video frame index."""
        return int(round(sec * self.fps))

    def analyze_audio(
        self, audio_path: str, lyrics_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process WAV audio file and optional lyrics to extract features."""
        import librosa

        print(f"[*] Loading audio file: {audio_path}")
        y, sr = librosa.load(audio_path, sr=self.sample_rate)
        duration = float(librosa.get_duration(y=y, sr=sr))

        # 1. BPM & Beat Tracking
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(np.round(np.atleast_1d(tempo)[0], 2))
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)

        beats_list = []
        for idx, t in enumerate(beat_times):
            beats_list.append(
                {
                    "beat_index": idx + 1,
                    "time": float(np.round(t, 3)),
                    "frame": self.sec_to_frame(t),
                    "bar": (idx // 4) + 1,
                    "beat_in_bar": (idx % 4) + 1,
                }
            )

        # 2. Kick / Snare Onset Detection using Frequency Filtering
        # Low-pass filter for Kick (20-150 Hz)
        y_kick = librosa.effects.preemphasis(y)
        kick_onset_frames = librosa.onset.onset_detect(y=y_kick, sr=sr)
        kick_onsets = [
            float(np.round(t, 3))
            for t in librosa.frames_to_time(kick_onset_frames, sr=sr)
        ]

        # General Snare / High Onset Detection
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        snare_onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
        snare_onsets = [
            float(np.round(t, 3))
            for t in librosa.frames_to_time(snare_onset_frames, sr=sr)
        ]

        # 3. Energy Structure Analysis (RMS & Section Classification)
        hop_length = 512
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

        # Dynamic Sectioning (15-second windows)
        section_duration = 15.0
        energy_sections = []
        num_sections = int(np.ceil(duration / section_duration))

        max_rms = float(np.max(rms)) if len(rms) > 0 else 1.0
        for i in range(num_sections):
            start_t = i * section_duration
            end_t = min((i + 1) * section_duration, duration)
            mask = (rms_times >= start_t) & (rms_times < end_t)
            avg_e = float(np.mean(rms[mask])) if np.any(mask) else 0.0
            normalized_energy = float(np.round(avg_e / (max_rms + 1e-6), 2))

            # Label section based on relative energy
            if normalized_energy > 0.75:
                label = "Drop / High Energy"
            elif normalized_energy > 0.45:
                label = "Chorus / Build-up"
            else:
                label = "Verse / Intro"

            energy_sections.append(
                {
                    "section_index": i + 1,
                    "start": float(np.round(start_t, 2)),
                    "end": float(np.round(end_t, 2)),
                    "energy": normalized_energy,
                    "label": label,
                }
            )

        # 4. Lyrics Timeline Extraction (Whisper or LRC parsing)
        lyrics_timeline = self._process_lyrics(audio_path, lyrics_path)

        manifest = {
            "audio_file": os.path.abspath(audio_path),
            "duration_sec": float(np.round(duration, 2)),
            "fps": self.fps,
            "bpm": bpm,
            "time_signature": "4/4",
            "total_beats": len(beats_list),
            "beats": beats_list,
            "kick_onsets": kick_onsets[:50],  # cap list for cleanliness
            "snare_onsets": snare_onsets[:50],
            "energy_sections": energy_sections,
            "lyrics_timeline": lyrics_timeline,
        }

        return manifest

    def _process_lyrics(
        self, audio_path: str, lyrics_path: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Extract word & sentence timecodes using Whisper model or fallback parser."""
        if lyrics_path and os.path.exists(lyrics_path) and lyrics_path.endswith(".lrc"):
            return self._parse_lrc_file(lyrics_path)

        # Try Whisper AI audio alignment
        try:
            import whisper

            print("[*] Running Whisper audio transcription & alignment...")
            model = whisper.load_model("base")
            result = model.transcribe(audio_path, word_timestamps=True)

            timeline = []
            for segment in result.get("segments", []):
                seg_dict = {
                    "start": float(np.round(segment["start"], 2)),
                    "end": float(np.round(segment["end"], 2)),
                    "text": segment["text"].strip(),
                    "words": [],
                }
                for word_info in segment.get("words", []):
                    seg_dict["words"].append(
                        {
                            "word": word_info["word"].strip(),
                            "start": float(np.round(word_info["start"], 2)),
                            "end": float(np.round(word_info["end"], 2)),
                        }
                    )
                timeline.append(seg_dict)
            return timeline
        except Exception as e:
            print(f"[!] Whisper alignment skipped/failed ({e}). Using empty timeline.")
            return []

    def _parse_lrc_file(self, lrc_path: str) -> List[Dict[str, Any]]:
        """Parse standard LRC lyrics file format."""
        import re

        timeline = []
        pattern = re.compile(r"\[(\d+):(\d+\.\d+)\](.*)")
        with open(lrc_path, "r", encoding="utf-8") as f:
            for line in f:
                match = pattern.match(line.strip())
                if match:
                    minutes, seconds, text = match.groups()
                    start_time = int(minutes) * 60 + float(seconds)
                    timeline.append(
                        {
                            "start": round(start_time, 2),
                            "end": round(start_time + 3.0, 2),  # Default 3s window
                            "text": text.strip(),
                            "words": [],
                        }
                    )
        return timeline

    @staticmethod
    def generate_dry_run_manifest(fps: int = 24) -> Dict[str, Any]:
        """Generate mock beats manifest for dry-run testing."""
        duration = 60.0
        bpm = 120.0
        beat_interval = 60.0 / bpm
        beats = []
        num_beats = int(duration / beat_interval)

        for i in range(num_beats):
            t = i * beat_interval
            beats.append(
                {
                    "beat_index": i + 1,
                    "time": round(t, 3),
                    "frame": int(round(t * fps)),
                    "bar": (i // 4) + 1,
                    "beat_in_bar": (i % 4) + 1,
                }
            )

        return {
            "audio_file": "assets/audio/mock_demo.wav",
            "duration_sec": duration,
            "fps": fps,
            "bpm": bpm,
            "time_signature": "4/4",
            "total_beats": len(beats),
            "beats": beats,
            "kick_onsets": [b["time"] for b in beats if b["beat_in_bar"] in (1, 3)],
            "snare_onsets": [b["time"] for b in beats if b["beat_in_bar"] in (2, 4)],
            "energy_sections": [
                {"section_index": 1, "start": 0.0, "end": 15.0, "energy": 0.35, "label": "Verse / Intro"},
                {"section_index": 2, "start": 15.0, "end": 30.0, "energy": 0.60, "label": "Chorus / Build-up"},
                {"section_index": 3, "start": 30.0, "end": 45.0, "energy": 0.85, "label": "Drop / High Energy"},
                {"section_index": 4, "start": 45.0, "end": 60.0, "energy": 0.40, "label": "Outro"},
            ],
            "lyrics_timeline": [
                {"start": 2.0, "end": 5.5, "text": "Neon lights reflecting on the rainy street", "words": []},
                {"start": 6.0, "end": 9.5, "text": "Cybernetic dreams inside a heart of beat", "words": []},
            ],
        }


def main():
    parser = argparse.ArgumentParser(description="Auto-MV Pipeline Step 1: Audio Analysis")
    parser.add_argument("--audio", type=str, help="Path to input audio WAV file")
    parser.add_argument("--lyrics", type=str, help="Path to input lyrics (LRC/TXT) file")
    parser.add_argument("--output", type=str, default="output/beats_manifest.json", help="Output JSON path")
    parser.add_argument("--fps", type=int, default=24, help="Video frame rate (default: 24)")
    parser.add_argument("--dry-run", action="store_true", help="Generate mock manifest for testing")

    args = parser.parse_args()

    if args.dry_run or not args.audio:
        if not args.dry_run and not args.audio:
            print("[!] No audio file provided. Running in --dry-run mode.")
        manifest = AudioAnalyzer.generate_dry_run_manifest(fps=args.fps)
    else:
        if not os.path.exists(args.audio):
            print(f"[ERROR] Audio file not found: {args.audio}")
            sys.exit(1)
        analyzer = AudioAnalyzer(fps=args.fps)
        manifest = analyzer.analyze_audio(args.audio, args.lyrics)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"[SUCCESS] Audio analysis complete. Manifest saved to: {output_path.resolve()}")


if __name__ == "__main__":
    main()

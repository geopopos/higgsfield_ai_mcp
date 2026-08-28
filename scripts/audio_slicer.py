#!/usr/bin/env python3
"""
Audio Vocal Segment Slicer
Slices full vocal stems into precise 5-second clips for Higgsfield/Seedance Lip-Sync using FFmpeg.
"""
import subprocess
import argparse
from pathlib import Path


def slice_vocal_segment(input_audio: str, start_time: str, duration: float, output_audio: str) -> bool:
    """
    Slice audio file using ffmpeg.
    
    Args:
        input_audio: Path to input audio file (WAV/MP3)
        start_time: Start timestamp in HH:MM:SS.mmm or seconds (e.g., '00:00:15.500' or '15.5')
        duration: Duration in seconds (e.g., 5.0)
        output_audio: Target file path
    """
    inp = Path(input_audio)
    out = Path(output_audio)
    out.parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-i", str(inp),
        "-t", str(duration),
        "-c:a", "pcm_s16le" if out.suffix.lower() == ".wav" else "copy",
        str(out)
    ]
    
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            print(f"✂️ Audio sliced: {start_time} (duration {duration}s) -> {out}")
            return True
        else:
            print(f"❌ FFmpeg error: {res.stderr}")
            return False
    except Exception as e:
        print(f"❌ Failed to run FFmpeg: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Slice Audio Stem for Lip-Sync")
    parser.add_argument("--input", type=str, required=True, help="Full vocal audio file")
    parser.add_argument("--start", type=str, required=True, help="Start time (e.g., 00:00:15.5)")
    parser.add_argument("--duration", type=float, default=5.0, help="Clip duration in seconds")
    parser.add_argument("--output", type=str, required=True, help="Output audio file path")
    args = parser.parse_args()
    
    slice_vocal_segment(args.input, args.start, args.duration, args.output)

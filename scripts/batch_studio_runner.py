#!/usr/bin/env python3
"""
AI Film Studio Batch Processor
Reads a project's manifest.json and automates Keyframe generation & DoP Video rendering via Higgsfield API.
"""
import os
import sys
import json
import asyncio
import argparse
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from higgsfield_mcp.client import HiggsfieldClient
except ImportError:
    from higgsfield_mcp.client import HiggsfieldClient


async def run_batch_studio(manifest_path: str, auto_download: bool = True):
    manifest_file = Path(manifest_path)
    if not manifest_file.exists():
        print(f"❌ Error: Manifest file not found at {manifest_path}")
        return

    project_dir = manifest_file.parent
    with open(manifest_file, "r", encoding="utf-8") as f:
        config = json.load(f)

    project_name = config.get("project_name", "unnamed_project")
    shots = config.get("shots", [])

    print(f"🎬 Starting batch rendering for project: {project_name}")
    print(f"📹 Found {len(shots)} shots to process.")

    api_key = os.getenv("HF_API_KEY", "")
    secret = os.getenv("HF_SECRET", "")

    if not api_key or not secret:
        print("⚠️ Warning: HF_API_KEY or HF_SECRET missing in environment. Running in dry-run/preview mode.")
        api_key = api_key or "dummy-key"
        secret = secret or "dummy-secret"

    client = HiggsfieldClient(api_key=api_key, secret=secret)
    renders_dir = project_dir / "04_renders"
    renders_dir.mkdir(parents=True, exist_ok=True)

    summary = []
    for shot in shots:
        shot_id = shot.get("shot_id", "shot")
        prompt = shot.get("prompt", "")
        motion_id = shot.get("motion_id", "camera_push_in")
        image_url = shot.get("image_url", "")

        print(f"\n🎥 [Shot {shot_id}] Prompt: {prompt[:60]}...")
        if image_url:
            print(f"   Generating Video (DoP) using motion: {motion_id}")
            try:
                res = await client.generate_video(image_url=image_url, motion_id=motion_id, prompt=prompt)
                job_id = res.get("job_set_id") or res.get("id")
                print(f"   ✅ Job queued successfully. Job ID: {job_id}")

                if auto_download and api_key != "dummy-key":
                    print(f"   ⏳ Polling and downloading render output to {renders_dir}...")
                    files = await client.poll_and_download(job_id, renders_dir)
                    print(f"   💾 Downloaded {len(files)} asset(s).")
                    summary.append({"shot_id": shot_id, "job_id": job_id, "status": "COMPLETED", "files": files})
                else:
                    summary.append({"shot_id": shot_id, "job_id": job_id, "status": "QUEUED"})
            except Exception as e:
                print(f"   ❌ Failed: {e}")
                summary.append({"shot_id": shot_id, "status": "FAILED", "error": str(e)})
        else:
            print(f"   Generating Image Keyframe (Soul)...")
            try:
                res = await client.generate_image(prompt=prompt)
                job_id = res.get("job_set_id") or res.get("id")
                print(f"   ✅ Job queued successfully. Job ID: {job_id}")

                if auto_download and api_key != "dummy-key":
                    print(f"   ⏳ Polling and downloading keyframe to {renders_dir}...")
                    files = await client.poll_and_download(job_id, renders_dir)
                    print(f"   💾 Downloaded {len(files)} asset(s).")
                    summary.append({"shot_id": shot_id, "job_id": job_id, "status": "COMPLETED", "files": files})
                else:
                    summary.append({"shot_id": shot_id, "job_id": job_id, "status": "QUEUED"})
            except Exception as e:
                print(f"   ❌ Failed: {e}")
                summary.append({"shot_id": shot_id, "status": "FAILED", "error": str(e)})

    # Write summary
    report_file = project_dir / "batch_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n📊 Batch execution complete. Report written to {report_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Film Studio Batch Processor")
    parser.add_argument("--manifest", type=str, required=True, help="Path to project manifest.json")
    parser.add_argument("--no-download", action="store_true", help="Queue jobs without waiting for download")
    args = parser.parse_args()

    asyncio.run(run_batch_studio(args.manifest, auto_download=not args.no_download))

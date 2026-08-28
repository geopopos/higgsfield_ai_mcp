from __future__ import annotations
import hashlib
import re
from .models import ShotDecision, MVProject, DirectorPolicy

class StoryPlanner:
    """Deterministic fallback planner. It never calls an LLM or video API."""
    DEFAULT_BEATS = ("establishing", "character", "action", "emotion", "hero", "resolution")

    def build_scenes(self, story: str, requested_scenes: list[dict] | None = None) -> list[dict]:
        if requested_scenes:
            return requested_scenes
        text = re.sub(r"\s+", " ", story.strip())
        chunks = [c.strip() for c in re.split(r"(?<=[。！？.!?])\s+", text) if c.strip()]
        if not chunks: chunks = [text]
        target = min(6, max(3, len(chunks)))
        scenes=[]
        for i in range(target):
            source = chunks[i % len(chunks)]
            beat = self.DEFAULT_BEATS[i]
            scenes.append({
                "scene_id": f"SCENE-{i+1:03d}",
                "description": f"{beat}: {source}",
                "shots": [
                    {"shot_id": f"SHOT-{i*2+1:03d}", "prompt": source, "camera": "wide" if i == 0 else "medium"},
                    {"shot_id": f"SHOT-{i*2+2:03d}", "prompt": f"Cinematic continuation of: {source}", "camera": "close_up" if i in (3,4) else "tracking"}
                ]
            })
        return scenes

class ShotPlanner:
    def __init__(self, client, policy: DirectorPolicy):
        self.client = client; self.policy = policy

    def plan(self, title, story, scenes):
        raw = self.client.director_plan(title, story, scenes, self.policy.aspect_ratio,
                                        self.policy.default_duration, "auto")
        shots=[]
        for r in raw["shots"]:
            # Quality-aware promotion: hero/final shots can be rendered at final resolution.
            q = r.get("quality", "auto")
            if q in ("final", "premium") and r["resolution"] == "720p":
                r["resolution"] = self.policy.final_resolution
            shots.append(ShotDecision(**{k:r.get(k) for k in ShotDecision.__dataclass_fields__ if k in r}))
        return MVProject(
            project_id="MV-" + hashlib.sha1(title.encode()).hexdigest()[:10],
            title=title, story=story, aspect_ratio=self.policy.aspect_ratio,
            shots=shots, estimated_twd=float(raw["estimated"]["estimated_twd"]),
            metadata={"planner":"deterministic-v1", "source":"gemini-video-mcp-v3.3"}
        )

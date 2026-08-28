from __future__ import annotations
from .models import MVProject, DirectorPolicy
from .planner import ShotPlanner
from gemini_video_mcp.client import VideoGenerationError

class ExecutionGuard:
    def __init__(self, client, policy): self.client=client; self.policy=policy
    def validate(self, project):
        if project.estimated_twd > self.policy.max_budget_twd:
            from gemini_video_mcp.client import VideoErrorCode
            raise VideoGenerationError(VideoErrorCode.BUDGET_EXCEEDED, f"Project estimate {project.estimated_twd:.2f} exceeds {self.policy.max_budget_twd:.2f}")
        for s in project.shots:
            self.client.validate_duration_ms(s.duration_seconds*1000, model=s.provider_model,
                resolution=s.resolution, has_reference=bool(s.reference_images))
        return {"approved": True, "estimated_twd": project.estimated_twd, "shot_count": len(project.shots)}

class ProjectExecutor:
    def __init__(self, client, policy): self.client=client; self.policy=policy

    def execute(self, project: MVProject, dry_run=False):
        guard=ExecutionGuard(self.client,self.policy)
        gate=guard.validate(project)
        if dry_run:
            return {"status":"dry_run","project":project.to_dict(),"gate":gate}
        project.status="executing"
        for shot in project.shots:
            try:
                result=self.client.generate_draft_video(
                    prompt=shot.prompt, duration_ms=shot.duration_seconds*1000,
                    reference_images=shot.reference_images, aspect_ratio=shot.aspect_ratio,
                    resolution=shot.resolution, quality=shot.quality, model=shot.provider_model,
                    shot_id=shot.shot_id, sequence_order=shot.sequence_order,
                    dialogue_script=shot.dialogue_script, sfx_cues=shot.sfx_cues,
                    ambient_audio=shot.ambient_audio, music_direction=shot.music_direction)
                shot.take_id=result.take_id; shot.state="generated"
                if self.policy.auto_activate and (not self.policy.require_qa):
                    self.client.set_take_active(result.take_id); shot.state="active"
            except Exception as e:
                shot.state="failed"; shot.error=str(e); project.status="failed"
                break
        else: project.status="completed"
        return project.to_dict()

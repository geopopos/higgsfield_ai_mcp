from __future__ import annotations
from dataclasses import asdict
import hashlib
import json
from .models import DirectorPolicy
from .planner import StoryPlanner, ShotPlanner
from .executor import ProjectExecutor

class MVDirectorEngine:
    """Upper layer: project lifecycle, planning, gates and explicit execution."""
    def __init__(self, client, policy: DirectorPolicy | None = None):
        self.client=client; self.policy=policy or DirectorPolicy()
        self.story=StoryPlanner(); self.shots=ShotPlanner(client,self.policy); self.executor=ProjectExecutor(client,self.policy)

    def create_plan(self, title, story, scenes=None, *, aspect_ratio=None, default_duration=None, quality="auto"):
        if aspect_ratio: self.policy.aspect_ratio=aspect_ratio
        if default_duration: self.policy.default_duration=default_duration
        scenes=self.story.build_scenes(story, scenes)
        project=self.shots.plan(title,story,scenes)
        project.metadata.update({"policy":asdict(self.policy),"quality":quality,"scene_count":len(scenes)})
        self.client.assets.event("mv_project_planned", {"project_id":project.project_id,"shots":len(project.shots)})
        return project.to_dict()

    def _project(self, d):
        from .models import MVProject, ShotDecision
        p=MVProject(project_id=d["project_id"],title=d["title"],story=d["story"],
                    status=d.get("status","draft"),aspect_ratio=d.get("aspect_ratio","16:9"),
                    estimated_twd=d.get("estimated_twd",0),spent_twd=d.get("spent_twd",0),metadata=d.get("metadata",{}))
        p.shots=[ShotDecision(**s) for s in d.get("shots",[])]
        return p

    @staticmethod
    def approval_token(project_dict):
        canonical=json.dumps(project_dict,sort_keys=True,ensure_ascii=False,separators=(",",":"))
        return hashlib.sha256(canonical.encode()).hexdigest()[:24]

    def dry_run(self, project_dict):
        p=self._project(project_dict)
        result=self.executor.execute(p,dry_run=True)
        result["approval_token"]=self.approval_token(project_dict)
        self.client.assets.event("mv_project_dry_run", {"project_id":p.project_id,"approval_token":result["approval_token"]})
        return result

    def execute(self, project_dict, approval_token=None):
        from gemini_video_mcp.client import VideoGenerationError, VideoErrorCode
        expected=self.approval_token(project_dict)
        if approval_token != expected:
            raise VideoGenerationError(VideoErrorCode.COST_GATE_LOCKED,
                "Execution requires the approval_token returned by a successful dry-run")
        p=self._project(project_dict)
        self.client.assets.event("mv_project_execution_started", {"project_id":p.project_id})
        result=self.executor.execute(p,dry_run=False)
        self.client.assets.event("mv_project_execution_finished", {"project_id":p.project_id,"status":result["status"]})
        return result

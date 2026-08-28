"""
Hierarchical Rollback Engine for AI MV Director Platform
Supports rollback_take, rollback_shot, rollback_scene, and rollback_project.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from .take_lineage import TakeLineageGraph, LineageNode


@dataclass
class RollbackReport:
    scope: str  # "take", "shot", "scene", "project"
    target_id: str
    affected_take_ids: List[str]
    restored_take_id: Optional[str]
    success: bool
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RollbackEngine:
    """Multi-tiered state recovery without destructive data loss."""

    def __init__(self, lineage_graph: TakeLineageGraph):
        self.lineage = lineage_graph

    def rollback_take(self, take_id: str, reason: str = "Manual take rollback") -> RollbackReport:
        node = self.lineage.get_take(take_id)
        if not node:
            return RollbackReport(scope="take", target_id=take_id, affected_take_ids=[], restored_take_id=None, success=False, reason="Take not found")

        self.lineage.set_status(take_id, "rolled_back")

        # Find previous valid take for this shot
        history = self.lineage.get_shot_history(node.shot_id)
        restored = None
        for cand in reversed(history):
            if cand.take_id != take_id and cand.status != "rolled_back":
                cand.status = "active"
                restored = cand.take_id
                break

        return RollbackReport(
            scope="take",
            target_id=take_id,
            affected_take_ids=[take_id],
            restored_take_id=restored,
            success=True,
            reason=f"{reason}. Restored previous take: {restored}",
        )

    def rollback_shot(self, shot_id: str, reason: str = "Shot reset") -> RollbackReport:
        history = self.lineage.get_shot_history(shot_id)
        affected = []
        for n in history:
            n.status = "rolled_back"
            affected.append(n.take_id)

        return RollbackReport(
            scope="shot",
            target_id=shot_id,
            affected_take_ids=affected,
            restored_take_id=None,
            success=True,
            reason=f"{reason}. All takes for shot {shot_id} rolled back to planned state.",
        )

    def rollback_scene(self, scene_id: str, reason: str = "Scene reset") -> RollbackReport:
        affected = []
        for node in self.lineage._nodes.values():
            if node.scene_id == scene_id:
                node.status = "rolled_back"
                affected.append(node.take_id)

        return RollbackReport(
            scope="scene",
            target_id=scene_id,
            affected_take_ids=affected,
            restored_take_id=None,
            success=True,
            reason=f"{reason}. Rolled back {len(affected)} takes in scene {scene_id}.",
        )

    def rollback_project(self, project_id: str, reason: str = "Project master reset") -> RollbackReport:
        affected = []
        for node in self.lineage._nodes.values():
            if node.project_id == project_id:
                node.status = "rolled_back"
                affected.append(node.take_id)

        return RollbackReport(
            scope="project",
            target_id=project_id,
            affected_take_ids=affected,
            restored_take_id=None,
            success=True,
            reason=f"{reason}. Full project reset performed. {len(affected)} takes marked rolled_back.",
        )

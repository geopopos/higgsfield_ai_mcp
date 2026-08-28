"""
Append-only Take Lineage Graph for AI MV Director Platform
Preserves all historical takes, derived takes, edits, extensions, and rejection records.
Node status may transition (e.g. candidate → active → rolled_back) but nodes are never deleted.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any


@dataclass
class LineageNode:
    take_id: str
    shot_id: str
    scene_id: str
    project_id: str
    parent_take_id: Optional[str]  # e.g., source take for edits/extensions
    derivation_type: str  # "initial", "retry", "stateful_edit", "extension", "upscale_4k"
    status: str  # "active", "candidate", "rejected", "rolled_back"
    qa_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TakeLineageGraph:
    """Immutable Directed Acyclic Graph of all generated takes."""

    def __init__(self):
        self._nodes: Dict[str, LineageNode] = {}
        self._shot_takes: Dict[str, List[str]] = {}

    def record_take(
        self,
        take_id: str,
        shot_id: str,
        scene_id: str,
        project_id: str,
        parent_take_id: Optional[str] = None,
        derivation_type: str = "initial",
        status: str = "candidate",
        qa_score: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LineageNode:
        node = LineageNode(
            take_id=take_id,
            shot_id=shot_id,
            scene_id=scene_id,
            project_id=project_id,
            parent_take_id=parent_take_id,
            derivation_type=derivation_type,
            status=status,
            qa_score=qa_score,
            metadata=metadata or {},
        )
        self._nodes[take_id] = node
        if shot_id not in self._shot_takes:
            self._shot_takes[shot_id] = []
        self._shot_takes[shot_id].append(take_id)
        return node

    def get_take(self, take_id: str) -> Optional[LineageNode]:
        return self._nodes.get(take_id)

    def get_shot_history(self, shot_id: str) -> List[LineageNode]:
        take_ids = self._shot_takes.get(shot_id, [])
        return [self._nodes[tid] for tid in take_ids if tid in self._nodes]

    def get_active_take_for_shot(self, shot_id: str) -> Optional[LineageNode]:
        history = self.get_shot_history(shot_id)
        for node in reversed(history):
            if node.status == "active":
                return node
        return history[-1] if history else None

    def set_status(self, take_id: str, status: str) -> bool:
        node = self._nodes.get(take_id)
        if node:
            node.status = status
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_takes": len(self._nodes),
            "nodes": [n.to_dict() for n in self._nodes.values()],
        }

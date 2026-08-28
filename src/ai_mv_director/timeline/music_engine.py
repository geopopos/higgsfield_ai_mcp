"""
Music-to-MV Timeline Engine for AI MV Director Platform
Transforms audio/musical attributes into deterministic downbeat, bar, energy, section, and cut-candidate timelines.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any


@dataclass(frozen=True)
class BeatMarker:
    timestamp_ms: int
    bar_index: int
    beat_in_bar: int
    is_downbeat: bool
    energy_level: float  # 0.0 to 1.0
    vocal_intensity: float  # 0.0 to 1.0
    is_cut_candidate: bool


@dataclass(frozen=True)
class MusicSection:
    section_name: str  # "intro", "verse", "pre-chorus", "chorus", "bridge", "outro"
    start_ms: int
    end_ms: int
    bars_count: int
    energy: float
    description: str = ""

    @property
    def duration_sec(self) -> float:
        return (self.end_ms - self.start_ms) / 1000.0


@dataclass
class TimelineCutCandidate:
    cut_id: str
    timestamp_ms: int
    bar_index: int
    musical_weight: float  # Higher on downbeats / chorus drops
    recommended_shot_type: str  # "HERO", "TRANSITION", "PERFORMANCE", "ACTION"
    reason: str


@dataclass
class MusicTimeline:
    total_duration_ms: int
    bpm: float
    time_signature: str = "4/4"
    sections: List[MusicSection] = field(default_factory=list)
    beat_markers: List[BeatMarker] = field(default_factory=list)
    cut_candidates: List[TimelineCutCandidate] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_duration_ms": self.total_duration_ms,
            "bpm": self.bpm,
            "time_signature": self.time_signature,
            "sections": [asdict(s) for s in self.sections],
            "beat_markers_count": len(self.beat_markers),
            "cut_candidates": [asdict(c) for c in self.cut_candidates],
        }


class MusicTimelineEngine:
    """Deterministic Musical Grid & Timeline Analyzer."""

    def __init__(self, bpm: float = 120.0, total_duration_sec: float = 240.0, beats_per_bar: int = 4):
        self.bpm = max(40.0, min(240.0, bpm))
        self.total_duration_ms = int(total_duration_sec * 1000)
        self.beats_per_bar = beats_per_bar
        self.ms_per_beat = (60.0 / self.bpm) * 1000.0

    def analyze(self, custom_sections: Optional[List[Dict[str, Any]]] = None) -> MusicTimeline:
        """Construct full beat grid, sections, energy curve, and cut candidates."""
        total_beats = int(self.total_duration_ms / self.ms_per_beat)
        
        # 1. Build Sections if not custom
        sections: List[MusicSection] = []
        if custom_sections:
            for s in custom_sections:
                sections.append(MusicSection(
                    section_name=s.get("name", "verse"),
                    start_ms=s.get("start_ms", 0),
                    end_ms=s.get("end_ms", 10000),
                    bars_count=s.get("bars", 4),
                    energy=s.get("energy", 0.5),
                    description=s.get("description", "")
                ))
        else:
            # Default standard Pop/MV 6-Act Structure
            dur = self.total_duration_ms
            sections = [
                MusicSection("intro", 0, int(dur * 0.10), int(total_beats * 0.10 / self.beats_per_bar), 0.3, "Ambient buildup"),
                MusicSection("verse_1", int(dur * 0.10), int(dur * 0.30), int(total_beats * 0.20 / self.beats_per_bar), 0.5, "Story exposition"),
                MusicSection("chorus_1", int(dur * 0.30), int(dur * 0.50), int(total_beats * 0.20 / self.beats_per_bar), 0.85, "First emotional explosion"),
                MusicSection("verse_2", int(dur * 0.50), int(dur * 0.65), int(total_beats * 0.15 / self.beats_per_bar), 0.55, "Parallel progression"),
                MusicSection("chorus_2_bridge", int(dur * 0.65), int(dur * 0.85), int(total_beats * 0.20 / self.beats_per_bar), 0.95, "Climax peak"),
                MusicSection("outro", int(dur * 0.85), dur, int(total_beats * 0.15 / self.beats_per_bar), 0.4, "Resolution & final fade"),
            ]

        # 2. Build Beat Grid & Cut Candidates
        beat_markers: List[BeatMarker] = []
        cut_candidates: List[TimelineCutCandidate] = []

        for b in range(total_beats):
            ts = int(b * self.ms_per_beat)
            if ts >= self.total_duration_ms:
                break
            
            bar_idx = b // self.beats_per_bar
            beat_in_bar = (b % self.beats_per_bar) + 1
            is_downbeat = (beat_in_bar == 1)

            # Determine section energy
            current_energy = 0.5
            for sec in sections:
                if sec.start_ms <= ts < sec.end_ms:
                    current_energy = sec.energy
                    break

            is_cut = is_downbeat and (bar_idx % 2 == 0)  # Cut on every 2 bars (standard pacing)
            beat_markers.append(BeatMarker(
                timestamp_ms=ts,
                bar_index=bar_idx,
                beat_in_bar=beat_in_bar,
                is_downbeat=is_downbeat,
                energy_level=current_energy,
                vocal_intensity=current_energy * 0.9,
                is_cut_candidate=is_cut,
            ))

            if is_cut:
                shot_type = "HERO" if current_energy >= 0.8 else ("PERFORMANCE" if current_energy >= 0.6 else "CHARACTER")
                cut_candidates.append(TimelineCutCandidate(
                    cut_id=f"cut_bar_{bar_idx}",
                    timestamp_ms=ts,
                    bar_index=bar_idx,
                    musical_weight=current_energy,
                    recommended_shot_type=shot_type,
                    reason=f"Downbeat on Bar {bar_idx+1} ({shot_type})",
                ))

        return MusicTimeline(
            total_duration_ms=self.total_duration_ms,
            bpm=self.bpm,
            time_signature=f"{self.beats_per_bar}/4",
            sections=sections,
            beat_markers=beat_markers,
            cut_candidates=cut_candidates,
        )

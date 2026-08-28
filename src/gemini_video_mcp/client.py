"""Gemini Video MCP v3.3 — Director Orchestration Edition.

Provider-neutral video orchestration with a real Veo 3.1 adapter, capability
validation, model routing, dynamic pricing, SQLite persistence, mock-first
execution, continuity QA, rollback-safe take lineage, HTTP API bridge,
budget enforcement, retry/backoff, thumbnail generation, and event analytics.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Model constants ──
MODEL_VEO_31 = "veo-3.1-generate-preview"
MODEL_VEO_31_FAST = "veo-3.1-fast-generate-preview"
MODEL_VEO_31_LITE = "veo-3.1-lite-generate-preview"
MODEL_OMNI_FLASH = "gemini-omni-1.1-flash"
MODEL_OMNI_PREVIEW = "gemini-omni-flash-preview"
MODEL_OMNI = MODEL_OMNI_FLASH
MODEL_VEO_FALLBACK = MODEL_VEO_31_FAST

# ── Duration / extension constants ──
SUPPORTED_DURATIONS = (4, 6, 8)
MIN_DURATION_SECONDS = 4.0
MAX_DURATION_SECONDS = 8.0
MAX_REFERENCE_IMAGES = 3
MAX_REFERENCE_VIDEOS = 1
EXTENSION_STEP_SECONDS = 7
MAX_EXTENSION_STEPS = 20
MAX_CUMULATIVE_EXTEND_SECONDS = 141
MAX_FINAL_EXTENSION_SECONDS = 148
OMNI_EXTENSION_STEP_SECONDS = 10
OMNI_MAX_TOTAL_SECONDS = 40
DEFAULT_USD_TWD_RATE = 32.0
ASSETS_DIR_NAME = ".assets"
ASSETS_DB_NAME = "assets_registry.json"
TAKES_DB_NAME = "takes_registry.json"
SQLITE_DB_NAME = "director.db"
CONTINUITY_WARN_THRESHOLD = 0.45
CONTINUITY_BLOCK_THRESHOLD = 0.20
VEO_VIDEO_STORAGE_TTL_HOURS = 48  # Veo API stores videos for 2 days

# ── Official Gemini API pricing, USD/sec ──
VIDEO_PRICING: dict[str, dict[str, float | str]] = {
    MODEL_VEO_31: {"720p": 0.40, "1080p": 0.40, "4k": 0.60, "note": "Veo 3.1 Standard with audio"},
    MODEL_VEO_31_FAST: {"720p": 0.10, "1080p": 0.12, "4k": 0.30, "note": "Veo 3.1 Fast with audio"},
    MODEL_VEO_31_LITE: {"720p": 0.05, "1080p": 0.08, "4k": 0.0, "note": "Veo 3.1 Lite; 4K unsupported"},
    MODEL_OMNI_FLASH: {"720p": 0.10, "1080p": 0.0, "4k": 0.0, "360p": 0.0, "note": "Token-billed; 5,792 output tokens/sec at 720p ≈ $0.10/sec effective; higher resolutions are billed by tokens"},
}

CAPABILITIES = {
    MODEL_VEO_31: {
        "text_to_video": True, "image_to_video": True, "reference_images": True,
        "max_reference_images": 3, "first_last_frame": True, "video_extension": True,
        "native_audio": True, "aspect_ratios": ["16:9", "9:16"],
        "durations": [4, 6, 8], "resolutions": ["720p", "1080p", "4k"],
        "max_extension_steps": 20, "extension_increment_seconds": 7,
    },
    MODEL_VEO_31_FAST: {
        "text_to_video": True, "image_to_video": True, "reference_images": True,
        "max_reference_images": 3, "first_last_frame": True, "video_extension": True,
        "native_audio": True, "aspect_ratios": ["16:9", "9:16"],
        "durations": [4, 6, 8], "resolutions": ["720p", "1080p", "4k"],
        "max_extension_steps": 20, "extension_increment_seconds": 7,
    },
    MODEL_VEO_31_LITE: {
        "text_to_video": True, "image_to_video": True, "reference_images": False,
        "max_reference_images": 0, "first_last_frame": False, "video_extension": False,
        "native_audio": True, "aspect_ratios": ["16:9", "9:16"],
        "durations": [4, 6, 8], "resolutions": ["720p", "1080p"],
        "max_extension_steps": 0, "extension_increment_seconds": 0,
    },
    MODEL_OMNI_FLASH: {
        "provider": "gemini-omni", "text_to_video": True, "image_to_video": True,
        "reference_images": True, "max_reference_images": 6,
        "first_last_frame": True, "video_extension": True, "stateful_editing": True,
        "native_audio": True, "aspect_ratios": ["16:9", "9:16"],
        "durations": list(range(3, 11)), "resolutions": ["360p", "720p", "1080p", "4k"],
        "max_extension_steps": 3, "extension_increment_seconds": 10,
        "max_total_extension_seconds": 40,
        "negative_prompt": False,
    },
}

MAX_RETRY_ATTEMPTS = 3
RETRY_BASE_DELAY = 2.0  # seconds, exponential backoff base


class VideoErrorCode(str, Enum):
    CONTINUITY_RISK = "CONTINUITY_RISK"
    COST_GATE_LOCKED = "COST_GATE_LOCKED"
    API_CAPABILITY_UNSUPPORTED = "API_CAPABILITY_UNSUPPORTED"
    MOCK_OUTPUT = "MOCK_OUTPUT"
    DURATION_OUT_OF_RANGE = "DURATION_OUT_OF_RANGE"
    GENERATION_FAILED = "GENERATION_FAILED"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    INTERACTION_NOT_FOUND = "INTERACTION_NOT_FOUND"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    INVALID_INPUT = "INVALID_INPUT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    OPERATION_TIMEOUT = "OPERATION_TIMEOUT"
    EXTENSION_LIMIT_EXCEEDED = "EXTENSION_LIMIT_EXCEEDED"
    VIDEO_EXPIRED = "VIDEO_EXPIRED"


class VideoGenerationError(Exception):
    def __init__(self, code: VideoErrorCode, message: str, details: dict | None = None):
        self.code, self.message, self.details = code, message, details or {}
        super().__init__(f"[{code.value}] {message}")


@dataclass
class CostEstimate:
    model: str
    resolution: str
    duration_seconds: float
    cost_usd: float
    cost_twd: float
    usd_twd_rate: float
    rate_timestamp: str
    pricing_source: str = "official-gemini-api"
    def to_dict(self): return asdict(self)


@dataclass
class ContinuityReport:
    histogram_score: float
    phash_score: float
    ssim_score: float
    combined_score: float
    risk_level: str
    details: dict = field(default_factory=dict)
    def to_dict(self): return asdict(self)


@dataclass
class TakeRecord:
    take_id: str
    asset_sha256: str
    file_path: str
    prompt: str
    negative_prompt: str | None = None
    model: str = MODEL_VEO_31_FAST
    resolution: str = "720p"
    duration_ms: int = 8000
    aspect_ratio: str = "16:9"
    # Cost split: estimated (real API cost) vs billable (0 for mock)
    estimated_cost_twd: float = 0.0
    billable_cost_twd: float = 0.0
    usd_twd_rate: float = DEFAULT_USD_TWD_RATE
    interaction_id: str | None = None
    previous_interaction_id: str | None = None
    parent_take_id: str | None = None
    provider_operation: str | None = None
    # v3.3: metadata fields
    shot_id: str | None = None
    sequence_order: int = 0
    extension_step: int = 0
    expires_at: str | None = None  # ISO timestamp when Veo storage expires
    thumbnail_path: str | None = None
    # v3.3: provider source tracking
    provider: str = "veo"
    is_mock: bool = False
    # Audio prompt fields (v3.3)
    dialogue_script: str | None = None
    sfx_cues: str | None = None
    ambient_audio: str | None = None
    music_direction: str | None = None
    # Standard fields
    status: str = "ready"
    qa_state: str = "pending"
    source_asset_shas: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def to_dict(self): return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TakeRecord":
        """Create from dict, ignoring unknown keys for backward compatibility."""
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in known}
        return cls(**filtered)


@dataclass
class TakeResult:
    take_id: str
    asset_sha256: str
    file_path: str
    interaction_id: str | None
    cost_estimate: CostEstimate
    status: str
    warnings: list[str]
    is_mock: bool = False
    provider: str = "veo"
    operation_id: str | None = None
    thumbnail_path: str | None = None
    def to_dict(self):
        return {
            "take_id": self.take_id, "asset_sha256": self.asset_sha256,
            "file_path": self.file_path, "interaction_id": self.interaction_id,
            "cost_estimate": self.cost_estimate.to_dict(), "status": self.status,
            "warnings": self.warnings, "is_mock": self.is_mock,
            "provider": self.provider, "operation_id": self.operation_id,
            "thumbnail_path": self.thumbnail_path,
        }


class AssetManager:
    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace).resolve()
        self.assets_dir = self.workspace / ASSETS_DIR_NAME
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.assets_db = self.assets_dir / ASSETS_DB_NAME
        self.takes_db = self.assets_dir / TAKES_DB_NAME
        self.sqlite_db = self.assets_dir / SQLITE_DB_NAME
        self._init_sqlite()

    def _init_sqlite(self):
        with sqlite3.connect(self.sqlite_db) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT, event TEXT, payload TEXT
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)")
            db.execute("""
                CREATE TABLE IF NOT EXISTS operations (
                    op_id TEXT PRIMARY KEY,
                    take_id TEXT, model TEXT, status TEXT,
                    created_at TEXT, completed_at TEXT,
                    error TEXT
                )
            """)

    def event(self, event: str, payload: dict):
        with sqlite3.connect(self.sqlite_db) as db:
            db.execute(
                "INSERT INTO events(ts,event,payload) VALUES(?,?,?)",
                (datetime.now(timezone.utc).isoformat(), event, json.dumps(payload, ensure_ascii=False))
            )

    def save_operation(self, op_id: str, take_id: str | None, model: str, status: str = "pending", error: str | None = None):
        with sqlite3.connect(self.sqlite_db) as db:
            db.execute(
                "INSERT OR REPLACE INTO operations(op_id,take_id,model,status,created_at,completed_at,error) VALUES(?,?,?,?,?,?,?)",
                (op_id, take_id or "", model, status, datetime.now(timezone.utc).isoformat(),
                 datetime.now(timezone.utc).isoformat() if status in ("done", "failed") else None, error)
            )

    def update_operation(self, op_id: str, status: str, error: str | None = None):
        with sqlite3.connect(self.sqlite_db) as db:
            completed = datetime.now(timezone.utc).isoformat() if status in ("done", "failed") else None
            db.execute(
                "UPDATE operations SET status=?, completed_at=COALESCE(?, completed_at), error=? WHERE op_id=?",
                (status, completed, error, op_id)
            )

    def get_pending_operations(self) -> list[dict]:
        with sqlite3.connect(self.sqlite_db) as db:
            rows = db.execute("SELECT op_id, take_id, model, status, created_at FROM operations WHERE status='pending'").fetchall()
            return [{"op_id": r[0], "take_id": r[1], "model": r[2], "status": r[3], "created_at": r[4]} for r in rows]

    def query_events(self, event_type: str | None = None, limit: int = 100) -> list[dict]:
        with sqlite3.connect(self.sqlite_db) as db:
            if event_type:
                rows = db.execute(
                    "SELECT ts, event, payload FROM events WHERE event=? ORDER BY ts DESC LIMIT ?",
                    (event_type, limit)
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT ts, event, payload FROM events ORDER BY ts DESC LIMIT ?", (limit,)
                ).fetchall()
            return [{"ts": r[0], "event": r[1], "payload": json.loads(r[2]) if r[2] else {}} for r in rows]

    def get_cost_summary(self) -> dict:
        """Aggregate cost analytics from takes registry."""
        takes = self._load_json(self.takes_db)
        total_estimated = sum(t.get("estimated_cost_twd", 0) for t in takes.values())
        total_billable = sum(t.get("billable_cost_twd", 0) for t in takes.values())
        by_model: dict[str, dict] = {}
        for t in takes.values():
            m = t.get("model", "unknown")
            if m not in by_model:
                by_model[m] = {"count": 0, "billable_twd": 0.0, "estimated_twd": 0.0}
            by_model[m]["count"] += 1
            by_model[m]["billable_twd"] += t.get("billable_cost_twd", 0)
            by_model[m]["estimated_twd"] += t.get("estimated_cost_twd", 0)
        return {
            "total_estimated_twd": round(total_estimated, 2),
            "total_billable_twd": round(total_billable, 2),
            "take_count": len(takes),
            "by_model": by_model,
        }

    def get_failure_stats(self) -> dict:
        """Count failed/rolled_back takes."""
        takes = self._load_json(self.takes_db)
        failed = sum(1 for t in takes.values() if t.get("qa_state") == "failed")
        rolled = sum(1 for t in takes.values() if t.get("status") == "rolled_back")
        return {"failed_qa": failed, "rolled_back": rolled, "total": len(takes)}

    def compute_sha256(self, file_path) -> str:
        path = Path(file_path)
        if not path.exists():
            raise VideoGenerationError(VideoErrorCode.FILE_NOT_FOUND, f"File not found: {path}")
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def register_asset(self, file_path, metadata=None) -> str:
        sha = self.compute_sha256(file_path)
        registry = self._load_json(self.assets_db)
        registry[sha] = {
            "sha256": sha, "file_path": str(Path(file_path).resolve()),
            "file_name": Path(file_path).name,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }
        self._save_json(self.assets_db, registry)
        self.event("asset.registered", registry[sha])
        return sha

    def get_asset(self, sha256) -> dict | None:
        return self._load_json(self.assets_db).get(sha256)

    def get_asset_path(self, sha256) -> Path | None:
        """Get resolved file path for an asset by SHA."""
        asset = self.get_asset(sha256)
        if not asset:
            return None
        p = Path(asset["file_path"])
        return p if p.exists() else None

    def register_take(self, take: TakeRecord):
        takes = self._load_json(self.takes_db)
        takes[take.take_id] = take.to_dict()
        self._save_json(self.takes_db, takes)
        self.event("take.registered", take.to_dict())

    def get_take(self, take_id) -> TakeRecord | None:
        d = self._load_json(self.takes_db).get(take_id)
        return TakeRecord.from_dict(d) if d else None

    def update_take(self, take_id, updates) -> TakeRecord | None:
        takes = self._load_json(self.takes_db)
        d = takes.get(take_id)
        if not d:
            return None
        d.update(updates)
        d["updated_at"] = datetime.now(timezone.utc).isoformat()
        takes[take_id] = d
        self._save_json(self.takes_db, takes)
        self.event("take.updated", {"take_id": take_id, "updates": updates})
        return TakeRecord.from_dict(d)

    def list_takes(self) -> list[TakeRecord]:
        return [TakeRecord.from_dict(d) for d in self._load_json(self.takes_db).values()]

    def list_takes_by_shot(self, shot_id: str) -> list[TakeRecord]:
        return [t for t in self.list_takes() if t.shot_id == shot_id]

    def get_active_take_for_shot(self, shot_id: str) -> TakeRecord | None:
        for t in self.list_takes_by_shot(shot_id):
            if t.status == "active":
                return t
        return None

    def _load_json(self, path) -> dict:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_json(self, path, data):
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)


class ModelRouter:
    """Capability-aware deterministic model selection. Explicit model always wins."""
    def __init__(self, preferred: str | None = None):
        self.preferred = preferred or os.getenv("GEMINI_VIDEO_MODEL", "")

    def choose(self, resolution: str, quality: str = "auto", has_references: bool = False, extension: bool = False) -> str:
        if self.preferred in CAPABILITIES:
            return self.preferred
        if quality in ("edit", "omni", "conversation"):
            return MODEL_OMNI_FLASH
        if extension or has_references:
            return MODEL_VEO_31_FAST if quality in ("draft", "fast", "auto") else MODEL_VEO_31
        if quality == "draft":
            return MODEL_VEO_31_LITE if resolution in ("720p", "1080p") else MODEL_VEO_31_FAST
        if quality == "final":
            return MODEL_VEO_31
        if resolution == "4k":
            return MODEL_VEO_31_FAST if quality != "premium" else MODEL_VEO_31
        return MODEL_VEO_31_FAST


class CostCalculator:
    def __init__(self, usd_twd_rate=None):
        self.rate = usd_twd_rate or float(os.getenv("USD_TWD_RATE", DEFAULT_USD_TWD_RATE))
        self.rate_timestamp = datetime.now(timezone.utc).isoformat()

    def estimate(self, resolution, duration_ms, model=MODEL_VEO_31_FAST) -> CostEstimate:
        sec = duration_ms / 1000.0
        model_price = VIDEO_PRICING.get(model, VIDEO_PRICING[MODEL_VEO_31_FAST])
        rate = float(model_price.get(resolution, 0.0))
        return CostEstimate(
            model, resolution, sec,
            round(rate * sec, 4),
            round(rate * sec * self.rate, 2),
            self.rate, self.rate_timestamp,
        )

    def check_budget(self, session_total_twd, session_cap_twd=None) -> bool:
        cap = session_cap_twd if session_cap_twd is not None else float(os.getenv("SESSION_BUDGET_TWD", "5000"))
        return session_total_twd <= cap

    def get_session_total_billable(self, assets: AssetManager) -> float:
        """Sum all billable costs from registered takes."""
        return sum(t.billable_cost_twd for t in assets.list_takes())


class ContinuityChecker:
    def __init__(self):
        try:
            from PIL import Image
            self._PIL = Image
        except ImportError:
            self._PIL = None
        try:
            import imagehash
            self._imagehash = imagehash
        except ImportError:
            self._imagehash = None
        try:
            from skimage.metrics import structural_similarity as ssim
            self._ssim = ssim
        except ImportError:
            self._ssim = None

    def _load(self, p):
        if not Path(p).exists():
            raise VideoGenerationError(VideoErrorCode.FILE_NOT_FOUND, f"Image not found: {p}")
        if not self._PIL:
            raise VideoGenerationError(VideoErrorCode.INVALID_INPUT, "Pillow is required for continuity QA")
        return self._PIL.open(p).convert("RGB")

    def check(self, start_img_path, end_img_path, block_threshold=CONTINUITY_BLOCK_THRESHOLD) -> ContinuityReport:
        import numpy as np
        a, b = self._load(start_img_path), self._load(end_img_path)
        x, y = np.array(a.resize((256, 256))), np.array(b.resize((256, 256)))
        h1 = np.histogram(x[:, :, 0], bins=64, range=(0, 255))[0].astype(float)
        h2 = np.histogram(y[:, :, 0], bins=64, range=(0, 255))[0].astype(float)
        hist = float(np.minimum(h1 / (h1.sum() + 1e-9), h2 / (h2.sum() + 1e-9)).sum())
        phash = 0.5
        if self._imagehash:
            p1, p2 = self._imagehash.phash(a), self._imagehash.phash(b)
            phash = max(0.0, min(1.0, 1.0 - (p1 - p2) / p1.hash.size))
        ssim_val = 0.5
        if self._ssim:
            from skimage.color import rgb2gray
            ssim_val = max(0.0, float(self._ssim(rgb2gray(x), rgb2gray(y), data_range=1.0)))
        combined = hist * .30 + phash * .30 + ssim_val * .40
        risk = "high_risk" if combined < block_threshold else "warning" if combined < CONTINUITY_WARN_THRESHOLD else "ok"
        return ContinuityReport(
            round(hist, 4), round(phash, 4), round(ssim_val, 4), round(combined, 4), risk,
            {"weights": {"histogram": .30, "phash": .30, "ssim": .40}},
        )


class AudioMetadataExtractor:
    def extract_prompt_metadata(self, audio_path) -> str:
        try:
            import librosa
            y, sr = librosa.load(audio_path, sr=22050, mono=True, duration=60)
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            bpm = float(tempo[0] if hasattr(tempo, "__len__") else tempo)
            times = librosa.frames_to_time(beats[:16], sr=sr)
            return (
                f"Music timing: {bpm:.0f} BPM; emphasize visual accents around beats at "
                f"{', '.join(f'{float(t):.2f}s' for t in times)}. "
                f"Preserve cinematic rhythm and natural sound design."
            )
        except Exception as e:
            logger.warning("Audio analysis fallback: %s", e)
            return (
                "Use the supplied music as the editorial rhythm reference; "
                "emphasize downbeats, transitions and vocal accents."
            )

    def build_audio_prompt(self, dialogue_script: str | None = None, sfx_cues: str | None = None,
                           ambient_audio: str | None = None, music_direction: str | None = None) -> str:
        """Build a native audio prompt section from structured audio fields."""
        parts = []
        if dialogue_script:
            parts.append(f'Dialogue: "{dialogue_script}"')
        if sfx_cues:
            parts.append(f"Sound effects: {sfx_cues}")
        if ambient_audio:
            parts.append(f"Ambient sound: {ambient_audio}")
        if music_direction:
            parts.append(f"Music: {music_direction}")
        return "\n".join(parts) if parts else ""


class ThumbnailGenerator:
    """Generate poster frames from video files using ffmpeg."""
    @staticmethod
    def generate(video_path, output_path=None, time_offset: float = 1.0) -> str | None:
        video_path = Path(video_path)
        if not video_path.exists():
            return None
        if output_path is None:
            output_path = video_path.with_suffix(".thumb.jpg")
        else:
            output_path = Path(output_path)
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return None
        try:
            cmd = [
                ffmpeg, "-y", "-ss", str(time_offset), "-i", str(video_path),
                "-frames:v", "1", "-q:v", "2", str(output_path)
            ]
            subprocess.run(cmd, capture_output=True, timeout=30, check=True)
            if output_path.exists():
                return str(output_path)
        except Exception:
            pass
        # Fallback for mock video files without decodable video stream
        try:
            from PIL import Image
            img = Image.new("RGB", (320, 180), color=(26, 26, 46))
            img.save(output_path, "JPEG")
            return str(output_path)
        except Exception:
            pass
        return None


class MockVideoGenerator:
    def generate(self, output_path, prompt, duration_seconds=8, resolution="720p"):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg = shutil.which("ffmpeg")
        sizes = {"720p": "1280x720", "1080p": "1920x1080", "4k": "3840x2160"}
        size = sizes.get(resolution, "1280x720")
        if ffmpeg:
            safe = prompt[:90].replace("'", " ").replace(":", " ")
            cmd = [
                ffmpeg, "-y", "-f", "lavfi",
                "-i", f"color=c=0x1a1a2e:s={size}:d={duration_seconds}:r=24",
                "-vf", f"drawtext=text='{safe}':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=(h-text_h)/2",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(output_path)
            ]
            try:
                subprocess.run(cmd, capture_output=True, timeout=60, check=True)
                return str(output_path)
            except Exception:
                pass
        output_path.write_bytes(b"MOCK_VIDEO_FILE\n" + prompt.encode() + b"\n")
        return str(output_path)


class DirectorOrchestrator:
    """Provider-neutral AI MV director layer: Story -> Scene -> Shot -> Route.

    Planning and dry-run are deterministic and never spend generation budget.
    Execution remains an explicit call to generation tools.
    """
    CAMERA_DEFAULTS = ("wide", "medium", "close_up", "over_shoulder", "tracking", "static")

    def __init__(self, client):
        self.client = client

    def plan(self, title: str, story: str, scenes: list[dict], aspect_ratio: str = "16:9",
             default_duration: int = 8, quality: str = "auto") -> dict:
        if not title.strip() or not story.strip():
            raise VideoGenerationError(VideoErrorCode.INVALID_INPUT, "title and story are required")
        if aspect_ratio not in ("16:9", "9:16"):
            raise VideoGenerationError(VideoErrorCode.INVALID_INPUT, "aspect_ratio must be 16:9 or 9:16")
        if default_duration not in (3, 4, 5, 6, 7, 8, 9, 10):
            raise VideoGenerationError(VideoErrorCode.INVALID_INPUT, "default_duration must be 3-10 seconds")
        shots=[]; order=0
        for si, scene in enumerate(scenes or [], 1):
            scene_id=scene.get("scene_id") or f"SCENE-{si:03d}"
            desc=str(scene.get("description") or scene.get("prompt") or "").strip()
            if not desc:
                raise VideoGenerationError(VideoErrorCode.INVALID_INPUT, f"scene {scene_id} has no description")
            raw_shots=scene.get("shots") or [{}]
            for raw in raw_shots:
                order += 1
                duration=int(raw.get("duration", default_duration))
                resolution=raw.get("resolution", "720p")
                q=raw.get("quality", quality)
                refs=raw.get("reference_images") or []
                extension=bool(raw.get("extension", False))
                model=self.client.router.choose(resolution, q, bool(refs), extension)
                self.client.validate_duration_ms(duration*1000, model=model, resolution=resolution,
                                                  has_reference=bool(refs), extension=extension)
                shot_id=raw.get("shot_id") or f"SHOT-{order:03d}"
                shots.append({
                    "shot_id":shot_id, "scene_id":scene_id, "sequence_order":order,
                    "prompt":raw.get("prompt") or desc,
                    "camera":raw.get("camera") or self.CAMERA_DEFAULTS[(order-1)%len(self.CAMERA_DEFAULTS)],
                    "duration_seconds":duration, "resolution":resolution,
                    "aspect_ratio":raw.get("aspect_ratio", aspect_ratio), "quality":q,
                    "provider_model":model, "reference_images":refs,
                    "transition":raw.get("transition", "cut"),
                    "dialogue_script":raw.get("dialogue_script"),
                    "sfx_cues":raw.get("sfx_cues"), "ambient_audio":raw.get("ambient_audio"),
                    "music_direction":raw.get("music_direction"),
                })
        return {"director_version":"3.3", "title":title, "story":story,
                "aspect_ratio":aspect_ratio, "shot_count":len(shots), "shots":shots,
                "estimated":self.estimate(shots)}

    def estimate(self, shots: list[dict]) -> dict:
        rows=[]; total=0.0
        for shot in shots:
            est=self.client.cost_calc.estimate(shot["resolution"], int(shot["duration_seconds"]*1000), shot["provider_model"])
            total += est.cost_twd
            rows.append({"shot_id":shot["shot_id"], "model":shot["provider_model"],
                         "usd":est.cost_usd, "twd":est.cost_twd})
        return {"estimated_twd":round(total,2), "shots":rows}

    def dry_run(self, plan: dict) -> dict:
        shots=plan.get("shots", [])
        return {"mode":"dry_run", "would_execute":len(shots),
                "estimated":plan.get("estimated", self.estimate(shots)), "shots":shots}

class GeminiVideoClient:
    def __init__(self, api_key=None, mock_mode=None, workspace=".", usd_twd_rate=None):
        self.mock_mode = (
            mock_mode if mock_mode is not None
            else os.getenv("MOCK_MODE", "false").lower() in ("1", "true", "yes")
        )
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.assets = AssetManager(workspace)
        self.cost_calc = CostCalculator(usd_twd_rate)
        self.continuity = ContinuityChecker()
        self.audio_extractor = AudioMetadataExtractor()
        self.router = ModelRouter()
        self.director = DirectorOrchestrator(self)
        self.mock_gen = MockVideoGenerator()
        self.thumbnail_gen = ThumbnailGenerator()
        self._api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self._genai_client = None
        if not self.mock_mode:
            self._init_genai_client()

    def _init_genai_client(self):
        try:
            from google import genai
            self._genai_client = genai.Client(api_key=self._api_key) if self._api_key else genai.Client()
        except Exception as e:
            raise VideoGenerationError(VideoErrorCode.PROVIDER_UNAVAILABLE, f"Google GenAI client unavailable: {e}")

    # ── Duration validation ──

    @staticmethod
    def validate_duration_ms(duration_ms, *, model=MODEL_VEO_31_FAST, resolution="720p",
                             has_reference=False, extension=False):
        if not isinstance(duration_ms, int) or duration_ms <= 0:
            raise VideoGenerationError(VideoErrorCode.DURATION_OUT_OF_RANGE, "duration_ms must be a positive integer")
        sec = duration_ms / 1000
        caps = CAPABILITIES.get(model)
        if not caps:
            raise VideoGenerationError(VideoErrorCode.API_CAPABILITY_UNSUPPORTED, f"Unknown model: {model}")
        if sec not in caps["durations"]:
            raise VideoGenerationError(VideoErrorCode.DURATION_OUT_OF_RANGE, f"{model} does not support {sec:g}s")
        if model in (MODEL_VEO_31, MODEL_VEO_31_FAST, MODEL_VEO_31_LITE):
            if (resolution in ("1080p", "4k") or has_reference or extension) and sec != 8:
                raise VideoGenerationError(
                    VideoErrorCode.DURATION_OUT_OF_RANGE,
                    "Veo 3.1 requires 8s when using references, extension, 1080p or 4K"
                )
        return sec

    # ── Budget enforcement ──

    def _check_budget_before_generation(self, projected_cost_twd: float):
        """Check if adding this cost would exceed session budget. Only for non-Mock."""
        if self.mock_mode:
            return  # Mock mode doesn't bill
        session_total = self.cost_calc.get_session_total_billable(self.assets)
        projected_total = session_total + projected_cost_twd
        if not self.cost_calc.check_budget(projected_total):
            cap = float(os.getenv("SESSION_BUDGET_TWD", "5000"))
            raise VideoGenerationError(
                VideoErrorCode.BUDGET_EXCEEDED,
                f"Projected session cost TWD {projected_total:.2f} exceeds budget TWD {cap:.2f}",
                {"session_total": session_total, "projected_cost": projected_cost_twd, "budget": cap}
            )

    # ── Veo API helpers ──

    def _image(self, p):
        from google.genai import types
        path = Path(p)
        if not path.exists():
            raise VideoGenerationError(VideoErrorCode.FILE_NOT_FOUND, f"Image not found: {p}")
        return types.Image.from_file(location=str(path)) if hasattr(types.Image, "from_file") else None

    def _build_config(self, model, resolution, aspect_ratio, duration_seconds,
                      reference_images=None, last_frame=None):
        from google.genai import types
        kwargs = {
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "duration_seconds": str(int(duration_seconds)),
            "number_of_videos": 1,
        }
        if reference_images:
            kwargs["reference_images"] = [
                types.VideoGenerationReferenceImage(image=self._image(p), reference_type="asset")
                for p in reference_images
            ]
        if last_frame:
            kwargs["last_frame"] = self._image(last_frame)
        return types.GenerateVideosConfig(**kwargs)

    def _omni_input_parts(self, prompt: str, reference_images: list[str] | None = None):
        parts = []
        for p in reference_images or []:
            path = Path(p)
            if not path.exists():
                raise VideoGenerationError(VideoErrorCode.FILE_NOT_FOUND, f"Image not found: {p}")
            mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(path.suffix.lower(), "image/jpeg")
            parts.append({"type": "image", "data": base64.b64encode(path.read_bytes()).decode("ascii"), "mime_type": mime})
        parts.append({"type": "text", "text": prompt})
        return parts

    def _run_omni_generate(self, *, prompt, model, resolution, aspect_ratio, duration_seconds, reference_images=None):
        if not self._genai_client or not hasattr(self._genai_client, "interactions"):
            raise VideoGenerationError(VideoErrorCode.PROVIDER_UNAVAILABLE, "Gemini SDK Interactions API is unavailable")
        response_format = {"type": "video", "aspect_ratio": aspect_ratio, "resolution": resolution, "delivery": "uri"}
        inputs = self._omni_input_parts(prompt, reference_images)
        try:
            interaction = self._genai_client.interactions.create(
                model=model, input=inputs if reference_images else prompt, response_format=response_format
            )
            op_id = getattr(interaction, "id", None) or f"omni_{uuid.uuid4().hex[:12]}"
            self.assets.save_operation(op_id, None, model, status="done")
            output = getattr(interaction, "output_video", None)
            if not output:
                raise VideoGenerationError(VideoErrorCode.GENERATION_FAILED, "Omni interaction returned no output_video")
            return output, op_id
        except VideoGenerationError:
            raise
        except Exception as e:
            raise VideoGenerationError(VideoErrorCode.GENERATION_FAILED, f"Omni generation failed: {e}")

    def _download_omni_video(self, output, output_path):
        data = getattr(output, "data", None)
        if data:
            Path(output_path).write_bytes(base64.b64decode(data))
            return str(output_path)
        uri = getattr(output, "uri", None)
        if uri and self._genai_client:
            try:
                payload = self._genai_client.files.download(file=uri)
                if isinstance(payload, (bytes, bytearray)):
                    Path(output_path).write_bytes(payload)
                    return str(output_path)
            except Exception as e:
                raise VideoGenerationError(VideoErrorCode.GENERATION_FAILED, f"Omni URI download failed: {e}")
        raise VideoGenerationError(VideoErrorCode.GENERATION_FAILED, "Omni output has no data or URI")

    def _run_veo_with_retry(self, *, prompt, model, resolution, aspect_ratio,
                             duration_seconds, image_path=None, last_frame=None,
                             reference_images=None, video=None) -> tuple:
        """Run Veo generation with exponential backoff retry for transient failures."""
        last_error = None
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                return self._run_veo_single(
                    prompt=prompt, model=model, resolution=resolution,
                    aspect_ratio=aspect_ratio, duration_seconds=duration_seconds,
                    image_path=image_path, last_frame=last_frame,
                    reference_images=reference_images, video=video,
                )
            except VideoGenerationError as e:
                last_error = e
                # Retry only on transient errors
                if e.code in (VideoErrorCode.OPERATION_TIMEOUT, VideoErrorCode.GENERATION_FAILED):
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning("Veo attempt %d failed: %s. Retrying in %.1fs", attempt + 1, e.message, delay)
                    time.sleep(delay)
                    continue
                raise  # Non-retryable errors
            except Exception as e:
                last_error = VideoGenerationError(VideoErrorCode.GENERATION_FAILED, f"Veo generation failed: {e}")
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning("Veo attempt %d failed: %s. Retrying in %.1fs", attempt + 1, e, delay)
                time.sleep(delay)
                continue
        raise last_error or VideoGenerationError(VideoErrorCode.GENERATION_FAILED, "All retry attempts exhausted")

    def _run_veo_single(self, *, prompt, model, resolution, aspect_ratio,
                        duration_seconds, image_path=None, last_frame=None,
                        reference_images=None, video=None) -> tuple:
        try:
            config = self._build_config(model, resolution, aspect_ratio, duration_seconds,
                                         reference_images, last_frame)
            image = self._image(image_path) if image_path else None
            kwargs = {"model": model, "prompt": prompt, "config": config}
            if image is not None:
                kwargs["image"] = image
            if video is not None:
                kwargs["video"] = video
            op = self._genai_client.models.generate_videos(**kwargs)
            # Persist operation ID immediately for resume capability
            op_id = getattr(op, "name", None) or f"op_{uuid.uuid4().hex[:12]}"
            self.assets.save_operation(op_id, "pending", model, status="pending")
            deadline = time.time() + int(os.getenv("VIDEO_OPERATION_TIMEOUT_SEC", "900"))
            poll_interval = int(os.getenv("VIDEO_POLL_SECONDS", "10"))
            while not op.done:
                if time.time() > deadline:
                    self.assets.update_operation(op_id, "failed", "Timeout")
                    raise VideoGenerationError(VideoErrorCode.OPERATION_TIMEOUT, "Video operation timed out")
                time.sleep(poll_interval)
                op = self._genai_client.operations.get(op)
            if getattr(op, "error", None):
                self.assets.update_operation(op_id, "failed", str(op.error))
                raise VideoGenerationError(VideoErrorCode.GENERATION_FAILED, str(op.error))
            self.assets.update_operation(op_id, "done")
            generated = op.response.generated_videos[0]
            return generated.video, op_id
        except VideoGenerationError:
            raise
        except Exception as e:
            raise VideoGenerationError(VideoErrorCode.GENERATION_FAILED, f"Veo generation failed: {e}")

    def _download_video(self, video, output_path) -> str:
        self._genai_client.files.download(file=video)
        if hasattr(video, "save"):
            video.save(str(output_path))
            return str(output_path)
        if getattr(video, "video_bytes", None):
            Path(output_path).write_bytes(video.video_bytes)
            return str(output_path)
        raise VideoGenerationError(VideoErrorCode.GENERATION_FAILED, "Generated video has no downloadable payload")

    # ── Take creation ──

    def _create_take(self, prompt, file_path, model, resolution, duration_ms, aspect_ratio,
                     warnings=None, parent_take_id=None, operation_id=None, interaction_id=None,
                     source_asset_shas=None, shot_id=None, sequence_order=0, extension_step=0,
                     expires_at=None, dialogue_script=None, sfx_cues=None,
                     ambient_audio=None, music_direction=None) -> tuple[TakeRecord, CostEstimate]:
        sha = self.assets.register_asset(file_path, {"model": model, "resolution": resolution, "duration_ms": duration_ms})
        cost = self.cost_calc.estimate(resolution, duration_ms, model)
        # Generate thumbnail
        thumb = ThumbnailGenerator.generate(file_path)
        take = TakeRecord(
            take_id=f"take_{uuid.uuid4().hex[:10]}",
            asset_sha256=sha,
            file_path=str(Path(file_path).resolve()),
            prompt=prompt,
            model=model,
            resolution=resolution,
            duration_ms=duration_ms,
            aspect_ratio=aspect_ratio,
            estimated_cost_twd=cost.cost_twd,
            billable_cost_twd=0.0 if self.mock_mode else cost.cost_twd,
            usd_twd_rate=cost.usd_twd_rate,
            interaction_id=interaction_id,
            parent_take_id=parent_take_id,
            provider_operation=operation_id,
            shot_id=shot_id,
            sequence_order=sequence_order,
            extension_step=extension_step,
            expires_at=expires_at,
            thumbnail_path=thumb,
            provider="mock" if self.mock_mode else ("gemini-omni" if model == MODEL_OMNI_FLASH else "veo"),
            is_mock=self.mock_mode,
            dialogue_script=dialogue_script,
            sfx_cues=sfx_cues,
            ambient_audio=ambient_audio,
            music_direction=music_direction,
            source_asset_shas=source_asset_shas or [],
            warnings=warnings or [],
        )
        self.assets.register_take(take)
        return take, cost

    def _mock_result(self, prompt, resolution, duration_ms, aspect_ratio, model,
                     warnings=None, parent_take_id=None, shot_id=None, sequence_order=0,
                     extension_step=0,
                     dialogue_script=None, sfx_cues=None, ambient_audio=None, music_direction=None) -> TakeResult:
        path = self.workspace / ASSETS_DIR_NAME / f"mock_{uuid.uuid4().hex[:10]}.mp4"
        self.mock_gen.generate(path, prompt, duration_ms / 1000, resolution)
        take, cost = self._create_take(
            prompt, str(path), model, resolution, duration_ms, aspect_ratio,
            warnings, parent_take_id, shot_id=shot_id, extension_step=extension_step,
            dialogue_script=dialogue_script, sfx_cues=sfx_cues,
            ambient_audio=ambient_audio, music_direction=music_direction,
        )
        take.status = "ready"
        self.assets.update_take(take.take_id, take.to_dict())
        return TakeResult(
            take.take_id, take.asset_sha256, take.file_path, None, cost,
            take.status, take.warnings, True, "mock", None, take.thumbnail_path,
        )

    # ── Extension validation ──

    def _validate_extension(self, parent_take: TakeRecord) -> tuple[int, str | None]:
        """Validate extension constraints. Returns (step, expires_at)."""
        caps = CAPABILITIES.get(parent_take.model, {})
        max_steps = caps.get("max_extension_steps", 0)
        if max_steps == 0:
            raise VideoGenerationError(
                VideoErrorCode.API_CAPABILITY_UNSUPPORTED,
                f"{parent_take.model} does not support video extension"
            )
        if parent_take.extension_step >= max_steps:
            raise VideoGenerationError(
                VideoErrorCode.EXTENSION_LIMIT_EXCEEDED,
                f"Maximum {max_steps} extension steps reached for this video"
            )
        # Check Veo storage TTL (2 days)
        if parent_take.expires_at and not self.mock_mode:
            expires = datetime.fromisoformat(parent_take.expires_at.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > expires:
                raise VideoGenerationError(
                    VideoErrorCode.VIDEO_EXPIRED,
                    f"Source video expired at {parent_take.expires_at}. Veo videos are stored for 2 days only."
                )
        if not self.mock_mode and not parent_take.provider_operation:
            raise VideoGenerationError(
                VideoErrorCode.INVALID_INPUT,
                "Extension source must be a Veo-generated video (no provider operation found)"
            )
        next_step = parent_take.extension_step + 1
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=VEO_VIDEO_STORAGE_TTL_HOURS)).isoformat()
        return next_step, expires_at

    # ── Public API methods ──

    def generate_draft_video(self, prompt, duration_ms, audio_clip_path=None,
                             reference_images=None, aspect_ratio="16:9",
                             resolution="720p", negative_prompt=None,
                             quality="auto", model=None, shot_id=None,
                             sequence_order=0, dialogue_script=None, sfx_cues=None,
                             ambient_audio=None, music_direction=None) -> TakeResult:
        refs = reference_images or []
        model = model or self.router.choose(resolution, quality, bool(refs))
        if model not in CAPABILITIES:
            raise VideoGenerationError(VideoErrorCode.API_CAPABILITY_UNSUPPORTED, f"Unknown model: {model}")
        if aspect_ratio not in CAPABILITIES[model]["aspect_ratios"]:
            raise VideoGenerationError(VideoErrorCode.INVALID_INPUT, f"Unsupported aspect ratio: {aspect_ratio}")
        if resolution not in CAPABILITIES[model]["resolutions"]:
            raise VideoGenerationError(VideoErrorCode.API_CAPABILITY_UNSUPPORTED, f"{model} does not support {resolution}")
        if len(refs) > CAPABILITIES[model]["max_reference_images"]:
            raise VideoGenerationError(
                VideoErrorCode.INVALID_INPUT,
                f"{model} accepts at most {CAPABILITIES[model]['max_reference_images']} reference images"
            )
        sec = self.validate_duration_ms(duration_ms, model=model, resolution=resolution, has_reference=bool(refs))

        # Build full prompt with audio
        full_prompt = prompt
        warnings = []
        if negative_prompt:
            full_prompt += f"\nAvoid: {negative_prompt}"

        # Audio prompt fields (v3.3 native audio via prompt)
        audio_prompt = self.audio_extractor.build_audio_prompt(
            dialogue_script, sfx_cues, ambient_audio, music_direction
        )
        if audio_prompt:
            full_prompt += "\n" + audio_prompt

        # External audio clip BPM analysis (fallback when no structured fields)
        if audio_clip_path and not audio_prompt:
            if not Path(audio_clip_path).exists():
                raise VideoGenerationError(VideoErrorCode.FILE_NOT_FOUND, f"Audio not found: {audio_clip_path}")
            if CAPABILITIES[model]["native_audio"]:
                full_prompt += "\n" + self.audio_extractor.extract_prompt_metadata(audio_clip_path)
            else:
                warnings.append("Selected provider has no native audio input; rhythm metadata was injected into prompt.")

        # Budget check
        cost = self.cost_calc.estimate(resolution, duration_ms, model)
        self._check_budget_before_generation(cost.cost_twd)

        if self.mock_mode:
            return self._mock_result(
                full_prompt, resolution, duration_ms, aspect_ratio, model,
                warnings, shot_id=shot_id, sequence_order=sequence_order,
                dialogue_script=dialogue_script, sfx_cues=sfx_cues,
                ambient_audio=ambient_audio, music_direction=music_direction,
            )

        # Provider dispatch
        if model == MODEL_OMNI_FLASH:
            video, op_id = self._run_omni_generate(
                prompt=full_prompt, model=model, resolution=resolution,
                aspect_ratio=aspect_ratio, duration_seconds=sec, reference_images=refs,
            )
        else:
            video, op_id = self._run_veo_with_retry(
                prompt=full_prompt, model=model, resolution=resolution,
                aspect_ratio=aspect_ratio, duration_seconds=sec, reference_images=refs,
            )
        path = self.workspace / ASSETS_DIR_NAME / f"veo_{uuid.uuid4().hex[:10]}.mp4"
        self._download_video(video, path)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=VEO_VIDEO_STORAGE_TTL_HOURS)).isoformat()
        take, cost = self._create_take(
            full_prompt, path, model, resolution, duration_ms, aspect_ratio,
            warnings, operation_id=op_id, shot_id=shot_id,
            sequence_order=sequence_order, expires_at=expires_at,
            dialogue_script=dialogue_script, sfx_cues=sfx_cues,
            ambient_audio=ambient_audio, music_direction=music_direction,
        )
        return TakeResult(
            take.take_id, take.asset_sha256, take.file_path, take.interaction_id,
            cost, take.status, take.warnings, False, "veo", op_id, take.thumbnail_path,
        )

    def generate_transition_video(self, start_img_path, end_img_path, duration_ms,
                                   prompt=None, resolution="720p", aspect_ratio="16:9",
                                   shot_id=None, sequence_order=0) -> TakeResult:
        report = self.continuity.check(start_img_path, end_img_path)
        warnings = []
        if report.risk_level != "ok":
            warnings.append(f"CONTINUITY_RISK score={report.combined_score}")
        model = self.router.choose(resolution, "fast", has_references=True)
        sec = self.validate_duration_ms(duration_ms, model=model, resolution=resolution, has_reference=True)
        prompt = prompt or (
            "Create a cinematic continuous transition from the first frame to the final frame "
            "with physically plausible motion and consistent character identity."
        )
        # Budget check
        cost = self.cost_calc.estimate(resolution, duration_ms, model)
        self._check_budget_before_generation(cost.cost_twd)

        if self.mock_mode:
            return self._mock_result(
                prompt, resolution, duration_ms, aspect_ratio, model,
                warnings, shot_id=shot_id, sequence_order=sequence_order,
            )

        video, op_id = self._run_veo_with_retry(
            prompt=prompt, model=model, resolution=resolution,
            aspect_ratio=aspect_ratio, duration_seconds=sec,
            image_path=start_img_path, last_frame=end_img_path,
        )
        path = self.workspace / ASSETS_DIR_NAME / f"transition_{uuid.uuid4().hex[:10]}.mp4"
        self._download_video(video, path)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=VEO_VIDEO_STORAGE_TTL_HOURS)).isoformat()
        source_shas = [self.assets.register_asset(start_img_path), self.assets.register_asset(end_img_path)]
        take, cost = self._create_take(
            prompt, path, model, resolution, duration_ms, aspect_ratio,
            warnings, operation_id=op_id, shot_id=shot_id,
            sequence_order=sequence_order, expires_at=expires_at,
            source_asset_shas=source_shas,
        )
        return TakeResult(
            take.take_id, take.asset_sha256, take.file_path, None, cost,
            take.status, take.warnings, False, "veo", op_id, take.thumbnail_path,
        )

    def extend_scene_video(self, video_ref_path, extend_sec,
                           character_anchor_img=None, prompt=None,
                           resolution="720p", aspect_ratio="16:9",
                           previous_interaction_id=None, shot_id=None,
                           sequence_order=0) -> TakeResult:
        if extend_sec != EXTENSION_STEP_SECONDS:
            raise VideoGenerationError(
                VideoErrorCode.INVALID_INPUT,
                f"Veo 3.1 extension is fixed at {EXTENSION_STEP_SECONDS} seconds per operation"
            )
        if resolution != "720p":
            raise VideoGenerationError(
                VideoErrorCode.API_CAPABILITY_UNSUPPORTED,
                "Veo 3.1 extension input/output is limited to 720p"
            )
        if not Path(video_ref_path).exists():
            raise VideoGenerationError(VideoErrorCode.FILE_NOT_FOUND, f"Video not found: {video_ref_path}")

        # Find parent take for extension metadata
        parent = self._find_take_by_file(video_ref_path)
        if not parent:
            raise VideoGenerationError(
                VideoErrorCode.INVALID_INPUT,
                "Extension source must be a registered Veo-generated video"
            )

        # Validate extension constraints
        next_step, expires_at = self._validate_extension(parent)

        model = self.router.choose("720p", "fast", extension=True)
        warnings = []
        if character_anchor_img:
            warnings.append(
                "Character anchor accepted as continuity metadata; "
                "Veo extension uses the previous Veo video as the extension source."
            )
        prompt = prompt or (
            "Continue the scene seamlessly. Preserve character identity, wardrobe, "
            "environment, lighting, camera language and motion continuity."
        )

        # Budget check
        cost = self.cost_calc.estimate("720p", EXTENSION_STEP_SECONDS * 1000, model)
        self._check_budget_before_generation(cost.cost_twd)

        if self.mock_mode:
            # Veo extension returns a combined video (original + 7s extension)
            # Track the added duration and total duration
            combined_duration = parent.duration_ms + (EXTENSION_STEP_SECONDS * 1000)
            return self._mock_result(
                prompt, "720p", combined_duration, aspect_ratio, model,
                warnings, parent_take_id=parent.take_id, shot_id=shot_id,
                sequence_order=sequence_order, extension_step=next_step,
            )

        # Upload and extend
        try:
            uploaded = self._genai_client.files.upload(file=video_ref_path)
            video = uploaded
        except Exception as e:
            raise VideoGenerationError(VideoErrorCode.GENERATION_FAILED, f"Extension source upload failed: {e}")

        generated, op_id = self._run_veo_with_retry(
            prompt=prompt, model=model, resolution="720p",
            aspect_ratio=aspect_ratio, duration_seconds=EXTENSION_STEP_SECONDS,
            video=video,
        )
        path = self.workspace / ASSETS_DIR_NAME / f"extend_{uuid.uuid4().hex[:10]}.mp4"
        self._download_video(generated, path)
        take, cost = self._create_take(
            prompt, path, model, "720p", EXTENSION_STEP_SECONDS * 1000, aspect_ratio,
            warnings, parent_take_id=parent.take_id, operation_id=op_id,
            shot_id=shot_id, sequence_order=sequence_order,
            extension_step=next_step, expires_at=expires_at,
        )
        return TakeResult(
            take.take_id, take.asset_sha256, take.file_path, None, cost,
            take.status, take.warnings, False, "veo", op_id, take.thumbnail_path,
        )

    def edit_take(self, previous_interaction_id, instruction, resolution=None, aspect_ratio=None):
        """Edit a Gemini Omni Flash interaction using stateful previous_interaction_id."""
        if not previous_interaction_id:
            raise VideoGenerationError(VideoErrorCode.INVALID_INPUT, "previous_interaction_id is required")
        response_format = {"type": "video"}
        if resolution:
            response_format["resolution"] = resolution
        if self.mock_mode:
            parent = self._find_take_by_interaction(previous_interaction_id)
            if not parent:
                raise VideoGenerationError(VideoErrorCode.INTERACTION_NOT_FOUND, f"Interaction not found: {previous_interaction_id}")
            result = self._mock_result(
                instruction, resolution or parent.resolution, parent.duration_ms,
                aspect_ratio or parent.aspect_ratio, MODEL_OMNI_FLASH,
                ["MOCK_OMNI_EDIT"], parent_take_id=parent.take_id,
                interaction_id=f"mock_edit_{uuid.uuid4().hex[:10]}",
                shot_id=parent.shot_id, sequence_order=parent.sequence_order,
            )
            return result
        if aspect_ratio:
            response_format["aspect_ratio"] = aspect_ratio
        if not self._genai_client or not hasattr(self._genai_client, "interactions"):
            raise VideoGenerationError(VideoErrorCode.PROVIDER_UNAVAILABLE, "Gemini SDK Interactions API is unavailable")
        try:
            res = self._genai_client.interactions.create(
                model=MODEL_OMNI_FLASH, previous_interaction_id=previous_interaction_id,
                input=instruction, response_format=response_format
            )
            output = getattr(res, "output_video", None)
            if not output:
                raise VideoGenerationError(VideoErrorCode.GENERATION_FAILED, "Omni edit returned no output_video")
            path = self.workspace / ASSETS_DIR_NAME / f"omni_edit_{uuid.uuid4().hex[:10]}.mp4"
            self._download_omni_video(output, path)
            take, cost = self._create_take(
                instruction, path, MODEL_OMNI_FLASH, resolution or "720p", 8000,
                aspect_ratio or "16:9", [], interaction_id=getattr(res, "id", None)
            )
            return TakeResult(take.take_id, take.asset_sha256, take.file_path, take.interaction_id,
                              cost, take.status, take.warnings, False, "gemini-omni",
                              getattr(res, "id", None), take.thumbnail_path)
        except VideoGenerationError:
            raise
        except Exception as e:
            raise VideoGenerationError(VideoErrorCode.GENERATION_FAILED, f"Omni edit failed: {e}")

    def upscale_video_4k(self, take_id) -> TakeResult:
        take = self.assets.get_take(take_id)
        if not take:
            raise VideoGenerationError(VideoErrorCode.INTERACTION_NOT_FOUND, f"Take not found: {take_id}")
        if take.qa_state != "passed" or take.status != "active":
            raise VideoGenerationError(VideoErrorCode.COST_GATE_LOCKED, "4K requires QA=passed and status=active")
        if take.resolution == "4k":
            return TakeResult(
                take.take_id, take.asset_sha256, take.file_path, take.interaction_id,
                self.cost_calc.estimate("4k", take.duration_ms, MODEL_VEO_31),
                take.status, take.warnings, take.is_mock, take.provider,
                take.provider_operation, take.thumbnail_path,
            )

        # Budget check for 4K
        cost = self.cost_calc.estimate("4k", take.duration_ms, MODEL_VEO_31)
        self._check_budget_before_generation(cost.cost_twd)

        if self.mock_mode:
            return self._mock_result(
                f"4K final render: {take.prompt}", "4k", take.duration_ms,
                take.aspect_ratio, MODEL_VEO_31, [], take.take_id,
                shot_id=take.shot_id, sequence_order=take.sequence_order,
            )

        if take.duration_ms != 8000:
            raise VideoGenerationError(VideoErrorCode.DURATION_OUT_OF_RANGE, "4K output requires an 8-second Veo 3.1 render")

        video, op_id = self._run_veo_with_retry(
            prompt=take.prompt, model=MODEL_VEO_31, resolution="4k",
            aspect_ratio=take.aspect_ratio, duration_seconds=8,
        )
        path = self.workspace / ASSETS_DIR_NAME / f"final4k_{uuid.uuid4().hex[:10]}.mp4"
        self._download_video(video, path)
        new_take, cost = self._create_take(
            take.prompt, path, MODEL_VEO_31, "4k", take.duration_ms,
            take.aspect_ratio, [], parent_take_id=take.take_id, operation_id=op_id,
            shot_id=take.shot_id, sequence_order=take.sequence_order,
            source_asset_shas=[take.asset_sha256],
            dialogue_script=take.dialogue_script, sfx_cues=take.sfx_cues,
            ambient_audio=take.ambient_audio, music_direction=take.music_direction,
        )
        self.assets.update_take(take_id, {"status": "finalized"})
        return TakeResult(
            new_take.take_id, new_take.asset_sha256, new_take.file_path, None,
            cost, new_take.status, new_take.warnings, False, "veo", op_id,
            new_take.thumbnail_path,
        )

    # ── Take management ──

    def set_take_active(self, take_id) -> TakeRecord | None:
        take = self.assets.get_take(take_id)
        if not take:
            return None
        if take.qa_state != "passed":
            raise VideoGenerationError(VideoErrorCode.COST_GATE_LOCKED, "QA must be passed before ACTIVE")
        # If this take belongs to a shot, deactivate other ACTIVE takes in the same shot
        if take.shot_id:
            for t in self.assets.list_takes_by_shot(take.shot_id):
                if t.status == "active" and t.take_id != take_id:
                    self.assets.update_take(t.take_id, {"status": "ready"})
        return self.assets.update_take(take_id, {"status": "active"})

    def set_take_qa(self, take_id, qa_state) -> TakeRecord | None:
        if qa_state not in ("pending", "passed", "failed"):
            raise VideoGenerationError(VideoErrorCode.INVALID_INPUT, "qa_state must be pending/passed/failed")
        return self.assets.update_take(take_id, {"qa_state": qa_state})

    def rollback_take(self, take_id) -> TakeRecord | None:
        take = self.assets.get_take(take_id)
        if not take:
            return None
        return self.assets.update_take(take_id, {"status": "rolled_back"})

    def list_takes(self) -> list[TakeRecord]:
        return self.assets.list_takes()

    def list_takes_by_shot(self, shot_id: str) -> list[TakeRecord]:
        return self.assets.list_takes_by_shot(shot_id)

    def get_take(self, take_id) -> TakeRecord | None:
        return self.assets.get_take(take_id)

    def director_plan(self, title: str, story: str, scenes: list[dict], aspect_ratio: str = "16:9",
                      default_duration: int = 8, quality: str = "auto") -> dict:
        plan=self.director.plan(title, story, scenes, aspect_ratio, default_duration, quality)
        self.assets.event("director_plan_created", {"title":title, "shot_count":plan["shot_count"]})
        return plan

    def director_dry_run(self, plan: dict) -> dict:
        result=self.director.dry_run(plan)
        self.assets.event("director_dry_run", {"shot_count":result["would_execute"]})
        return result

    def get_capabilities(self) -> dict:
        return CAPABILITIES

    def get_pricing(self) -> dict:
        return VIDEO_PRICING

    def get_router_status(self) -> dict:
        return {
            "preferred_model": self.router.preferred or None,
            "available_models": list(CAPABILITIES.keys()),
            "mock_mode": self.mock_mode,
        }

    # ── Analytics ──

    def get_cost_summary(self) -> dict:
        return self.assets.get_cost_summary()

    def get_failure_stats(self) -> dict:
        return self.assets.get_failure_stats()

    def get_event_log(self, event_type: str | None = None, limit: int = 100) -> list[dict]:
        return self.assets.query_events(event_type, limit)

    def get_pending_operations(self) -> list[dict]:
        return self.assets.get_pending_operations()

    # ── Final output pipeline ──

    def export_timeline(self, shot_ids: list[str] | None = None) -> dict:
        """Export ACTIVE takes as a timeline for concatenation. Returns EDL-like structure."""
        if shot_ids:
            takes = []
            for sid in shot_ids:
                takes.extend(self.assets.list_takes_by_shot(sid))
        else:
            takes = self.assets.list_takes()
        active = [t for t in takes if t.status in ("active", "final")]
        active.sort(key=lambda t: (t.shot_id or "", t.sequence_order))
        return {
            "timeline": [
                {
                    "order": i + 1,
                    "shot_id": t.shot_id,
                    "take_id": t.take_id,
                    "file_path": t.file_path,
                    "duration_ms": t.duration_ms,
                    "resolution": t.resolution,
                    "thumbnail_path": t.thumbnail_path,
                }
                for i, t in enumerate(active)
            ],
            "total_duration_ms": sum(t.duration_ms for t in active),
            "take_count": len(active),
        }

    def concat_active_takes(self, output_path: str | None = None) -> str | None:
        """Concatenate all ACTIVE/finalized takes into a single MP4 using ffmpeg."""
        timeline = self.export_timeline()
        if not timeline["take_count"]:
            return None
        active_takes = [t for t in self.list_takes() if t.status in ("active", "final")]
        active_takes.sort(key=lambda t: (t.shot_id or "", t.sequence_order))
        if output_path is None:
            output_path = str(self.workspace / ASSETS_DIR_NAME / f"final_{uuid.uuid4().hex[:8]}.mp4")
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return None
        # Create concat list file
        list_file = self.workspace / ASSETS_DIR_NAME / f"concat_{uuid.uuid4().hex[:8]}.txt"
        lines = []
        for t in active_takes:
            lines.append(f"file '{t.file_path}'")
        list_file.write_text("\n".join(lines), encoding="utf-8")
        try:
            cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", output_path]
            subprocess.run(cmd, capture_output=True, timeout=300, check=True)
            return output_path
        except Exception as e:
            logger.error("Concat failed: %s", e)
            return None
        finally:
            list_file.unlink(missing_ok=True)

    # ── Helpers ──

    def _find_take_by_file(self, path) -> TakeRecord | None:
        target = str(Path(path).resolve())
        for t in self.assets.list_takes():
            if str(Path(t.file_path).resolve()) == target:
                return t
        return None

    def _find_take_by_interaction(self, interaction_id) -> TakeRecord | None:
        for t in self.assets.list_takes():
            if t.interaction_id == interaction_id:
                return t
        return None

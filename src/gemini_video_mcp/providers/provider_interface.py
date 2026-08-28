"""
Isolated Provider Layer for Gemini Video MCP & AI MV Director
Defines VideoProvider ABC and isolated MockProvider, VeoProvider, and OmniProvider classes.
"""

from __future__ import annotations
import os
import time
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any


@dataclass
class ProviderResponse:
    provider: str
    model: str
    take_id: str
    asset_sha256: str
    file_path: str
    duration_sec: float
    resolution: str
    is_mock: bool
    billable_cost_usd: float
    billable_cost_twd: float
    thumbnail_path: Optional[str] = None
    warnings: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["warnings"] = self.warnings or []
        return d


class VideoProvider(ABC):
    """Abstract Base Class for Video Generation Providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        duration_sec: float,
        resolution: str = "720p",
        aspect_ratio: str = "16:9",
        reference_images: Optional[List[str]] = None,
        first_frame_path: Optional[str] = None,
        last_frame_path: Optional[str] = None,
        input_video_path: Optional[str] = None,
    ) -> ProviderResponse:
        pass


class MockProvider(VideoProvider):
    """Zero-credential Mock Provider with deterministic artifact hashes."""

    def __init__(self, workspace: str):
        self.workspace = workspace
        self.assets_dir = os.path.join(workspace, ".assets")
        os.makedirs(self.assets_dir, exist_ok=True)

    def generate(
        self,
        prompt: str,
        duration_sec: float,
        resolution: str = "720p",
        aspect_ratio: str = "16:9",
        reference_images: Optional[List[str]] = None,
        first_frame_path: Optional[str] = None,
        last_frame_path: Optional[str] = None,
        input_video_path: Optional[str] = None,
    ) -> ProviderResponse:
        content_seed = f"mock_{prompt}_{duration_sec}_{resolution}_{time.time()}"
        sha = hashlib.sha256(content_seed.encode("utf-8")).hexdigest()
        take_id = f"take_{sha[:10]}"
        file_path = os.path.join(self.assets_dir, f"mock_{sha[:10]}.mp4")
        thumb_path = os.path.join(self.assets_dir, f"mock_{sha[:10]}.thumb.jpg")

        # Create dummy mock files
        if not os.path.exists(file_path):
            with open(file_path, "wb") as f:
                f.write(b"MOCK_VIDEO_BINARY_DATA")
        if not os.path.exists(thumb_path):
            with open(thumb_path, "wb") as f:
                f.write(b"MOCK_THUMBNAIL_JPEG_DATA")

        return ProviderResponse(
            provider="mock",
            model="mock-engine",
            take_id=take_id,
            asset_sha256=sha,
            file_path=file_path,
            duration_sec=duration_sec,
            resolution=resolution,
            is_mock=True,
            billable_cost_usd=0.0,
            billable_cost_twd=0.0,
            thumbnail_path=thumb_path,
            warnings=[],
        )


class VeoProvider(VideoProvider):
    """Live Google Veo 3.1 Video Generation Provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required for live VeoProvider.")

    def generate(
        self,
        prompt: str,
        duration_sec: float,
        resolution: str = "720p",
        aspect_ratio: str = "16:9",
        reference_images: Optional[List[str]] = None,
        first_frame_path: Optional[str] = None,
        last_frame_path: Optional[str] = None,
        input_video_path: Optional[str] = None,
    ) -> ProviderResponse:
        # STUB: This is a placeholder implementation.
        # TODO: Replace with actual google.genai Veo 3.1 API call:
        #   operation = client.models.generate_videos(model=..., prompt=..., config=...)
        #   Poll operation, download result, compute real SHA256, record real billing.
        from google import genai
        client = genai.Client(api_key=self.api_key)
        raise NotImplementedError(
            "VeoProvider.generate() is a stub. Set mock_mode=True or implement "
            "the actual google.genai video generation call."
        )


class OmniProvider(VideoProvider):
    """Live Google Gemini Omni 1.1 Flash Video Generation Provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required for live OmniProvider.")

    def generate(
        self,
        prompt: str,
        duration_sec: float,
        resolution: str = "720p",
        aspect_ratio: str = "16:9",
        reference_images: Optional[List[str]] = None,
        first_frame_path: Optional[str] = None,
        last_frame_path: Optional[str] = None,
        input_video_path: Optional[str] = None,
    ) -> ProviderResponse:
        # STUB: This is a placeholder implementation.
        # TODO: Replace with actual google.genai Gemini Omni 1.1 Flash API call:
        #   response = client.models.generate_content(model="gemini-2.0-flash-preview-image-generation", ...)
        #   Extract video from response parts, save to disk, compute SHA256.
        raise NotImplementedError(
            "OmniProvider.generate() is a stub. Set mock_mode=True or implement "
            "the actual google.genai omni generation call."
        )

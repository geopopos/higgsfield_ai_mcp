"""
FastAPI HTTP Bridge — Gemini Video MCP v3.2
=======================================

將 MCP tools 暴露為 REST API 端點，讓前端可以直接呼叫。
資產透過 SHA-256 雜湊安全提供，不暴露任意檔案路徑。

安全預設：
  • 預設綁定 127.0.0.1
  • Mock 模式預設開啟
  • 資產只透過註冊的 SHA 提供

啟動方式：
  python -m gemini_video_mcp.api
  # 或
  uvicorn gemini_video_mcp.api:app --host 127.0.0.1 --port 8765
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Annotated

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))
API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN", "").strip()

from .client import (
    GeminiVideoClient,
    VideoErrorCode,
    VideoGenerationError,
    EXTENSION_STEP_SECONDS,
)
import uuid

ASSETS_DIR_NAME = ".assets"

# ──────────────────────────────────────────────
# 初始化
# ──────────────────────────────────────────────

def _create_client() -> GeminiVideoClient:
    mock = os.getenv("MOCK_MODE", "true").lower() in ("true", "1", "yes")
    workspace = os.getenv("WORKSPACE_DIR", ".")
    rate_str = os.getenv("USD_TWD_RATE")
    rate = float(rate_str) if rate_str else None
    return GeminiVideoClient(mock_mode=mock, workspace=workspace, usd_twd_rate=rate)


app = FastAPI(
    title="Gemini Video MCP v3.2 — Director API",
    description="HTTP bridge for Veo 3.1 video generation pipeline",
    version="3.2.0",
)

# CORS: 預設允許 localhost
allowed_origins = [o.strip() for o in os.getenv("API_CORS_ORIGINS", "http://localhost,http://127.0.0.1,https://www.perplexity.ai").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Optional bearer auth. Disabled only when API_AUTH_TOKEN is empty."""
    if API_AUTH_TOKEN and request.url.path.startswith("/api/"):
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {API_AUTH_TOKEN}":
            return JSONResponse(status_code=401, content={"error": True, "message": "Unauthorized"})
    return await call_next(request)

_client: GeminiVideoClient | None = None


def get_client() -> GeminiVideoClient:
    global _client
    if _client is None:
        _client = _create_client()
    return _client


def _result_to_take_dict(client: GeminiVideoClient, result) -> dict:
    """Convert TakeResult to a full TakeRecord dict for frontend consumption.
    Merges cost_estimate and operation_id from TakeResult into the persisted TakeRecord."""
    take = client.get_take(result.take_id)
    if take is None:
        # Fallback to TakeResult dict if take not persisted yet
        return result.to_dict()
    d = take.to_dict()
    # Merge cost estimate details
    d["cost_estimate"] = result.cost_estimate.to_dict()
    d["operation_id"] = result.operation_id
    d["thumbnail_path"] = result.thumbnail_path or take.thumbnail_path
    return d


def _error_response(e: VideoGenerationError):
    return JSONResponse(
        status_code=400,
        content={
            "error": True,
            "error_code": e.code.value,
            "message": e.message,
            "details": e.details,
        },
    )


# ──────────────────────────────────────────────
# Pydantic 模型
# ──────────────────────────────────────────────

class DraftRequest(BaseModel):
    prompt: str
    duration_ms: int = 8000
    audio_clip_path: str | None = None
    reference_images: list[str] | None = None
    aspect_ratio: str = "16:9"
    resolution: str = "720p"
    negative_prompt: str | None = None
    quality: str = "auto"
    shot_id: str | None = None
    sequence_order: int = 0
    dialogue_script: str | None = None
    sfx_cues: str | None = None
    ambient_audio: str | None = None
    music_direction: str | None = None


class TransitionRequest(BaseModel):
    start_img_path: str
    end_img_path: str
    duration_ms: int = 8000
    prompt: str | None = None
    resolution: str = "720p"
    aspect_ratio: str = "16:9"
    shot_id: str | None = None
    sequence_order: int = 0


class ExtendRequest(BaseModel):
    video_ref_path: str
    extend_sec: int = EXTENSION_STEP_SECONDS
    character_anchor_img: str | None = None
    prompt: str | None = None
    resolution: str = "720p"
    aspect_ratio: str = "16:9"
    previous_interaction_id: str | None = None
    shot_id: str | None = None
    sequence_order: int = 0


class QARequest(BaseModel):
    qa_state: str = "pending"


class TimelineExportRequest(BaseModel):
    shot_ids: list[str] | None = None


class ConcatRequest(BaseModel):
    output_path: str | None = None


# ──────────────────────────────────────────────
# 端點：系統狀態
# ──────────────────────────────────────────────

@app.get("/api/status")
async def get_status():
    """取得系統狀態。"""
    client = get_client()
    return {
        "version": "3.2.0",
        "mock_mode": client.mock_mode,
        "router": client.get_router_status(),
        "workspace": str(client.workspace),
        "take_count": len(client.list_takes()),
    }


@app.get("/api/capabilities")
async def get_capabilities():
    """取得 API 能力偵測。"""
    return get_client().get_capabilities()


@app.get("/api/pricing")
async def get_pricing():
    """取得定價表。"""
    return get_client().get_pricing()


# ──────────────────────────────────────────────
# 端點：影片生成
# ──────────────────────────────────────────────

@app.post("/api/generate/draft")
async def generate_draft(req: DraftRequest):
    """生成 720p 草稿影片。"""
    try:
        client = get_client()
        result = client.generate_draft_video(
            prompt=req.prompt,
            duration_ms=req.duration_ms,
            audio_clip_path=req.audio_clip_path,
            reference_images=req.reference_images,
            aspect_ratio=req.aspect_ratio,
            resolution=req.resolution,
            negative_prompt=req.negative_prompt,
            quality=req.quality,
            shot_id=req.shot_id,
            sequence_order=req.sequence_order,
            dialogue_script=req.dialogue_script,
            sfx_cues=req.sfx_cues,
            ambient_audio=req.ambient_audio,
            music_direction=req.music_direction,
        )
        return _result_to_take_dict(client, result)
    except VideoGenerationError as e:
        return _error_response(e)
    except Exception as e:
        return _error_response(VideoGenerationError(
            VideoErrorCode.GENERATION_FAILED, f"Unexpected error: {e}"
        ))


@app.post("/api/generate/transition")
async def generate_transition(req: TransitionRequest):
    """生成首尾幀轉場。"""
    try:
        client = get_client()
        result = client.generate_transition_video(
            start_img_path=req.start_img_path,
            end_img_path=req.end_img_path,
            duration_ms=req.duration_ms,
            prompt=req.prompt,
            resolution=req.resolution,
            aspect_ratio=req.aspect_ratio,
            shot_id=req.shot_id,
            sequence_order=req.sequence_order,
        )
        return _result_to_take_dict(client, result)
    except VideoGenerationError as e:
        return _error_response(e)
    except Exception as e:
        return _error_response(VideoGenerationError(
            VideoErrorCode.GENERATION_FAILED, f"Unexpected error: {e}"
        ))


@app.post("/api/generate/extend")
async def generate_extend(req: ExtendRequest):
    """延伸場景影片。"""
    try:
        client = get_client()
        result = client.extend_scene_video(
            video_ref_path=req.video_ref_path,
            extend_sec=req.extend_sec,
            character_anchor_img=req.character_anchor_img,
            prompt=req.prompt,
            resolution=req.resolution,
            aspect_ratio=req.aspect_ratio,
            previous_interaction_id=req.previous_interaction_id,
            shot_id=req.shot_id,
            sequence_order=req.sequence_order,
        )
        return _result_to_take_dict(client, result)
    except VideoGenerationError as e:
        return _error_response(e)
    except Exception as e:
        return _error_response(VideoGenerationError(
            VideoErrorCode.GENERATION_FAILED, f"Unexpected error: {e}"
        ))


@app.post("/api/upscale-4k/{take_id}")
async def upscale_4k(take_id: str):
    """4K 升頻。"""
    try:
        client = get_client()
        result = client.upscale_video_4k(take_id)
        return _result_to_take_dict(client, result)
    except VideoGenerationError as e:
        return _error_response(e)
    except Exception as e:
        return _error_response(VideoGenerationError(
            VideoErrorCode.GENERATION_FAILED, f"Unexpected error: {e}"
        ))


# ──────────────────────────────────────────────
# 端點：Take 管理
# ──────────────────────────────────────────────

@app.get("/api/takes")
async def list_takes(shot_id: str | None = Query(None)):
    """列出所有 Take（可按 shot_id 過濾）。"""
    client = get_client()
    if shot_id:
        takes = client.list_takes_by_shot(shot_id)
    else:
        takes = client.list_takes()
    return [t.to_dict() for t in takes]


@app.get("/api/takes/{take_id}")
async def get_take(take_id: str):
    """查詢指定 Take。"""
    client = get_client()
    take = client.get_take(take_id)
    if take is None:
        raise HTTPException(status_code=404, detail=f"Take not found: {take_id}")
    return take.to_dict()


@app.put("/api/takes/{take_id}/qa")
async def set_take_qa(take_id: str, req: QARequest):
    """設定 QA 狀態。"""
    try:
        client = get_client()
        take = client.set_take_qa(take_id, req.qa_state)
        if take is None:
            raise HTTPException(status_code=404, detail=f"Take not found: {take_id}")
        return take.to_dict()
    except VideoGenerationError as e:
        return _error_response(e)


@app.put("/api/takes/{take_id}/active")
async def set_take_active(take_id: str):
    """設為 ACTIVE。"""
    try:
        client = get_client()
        take = client.set_take_active(take_id)
        if take is None:
            raise HTTPException(status_code=404, detail=f"Take not found: {take_id}")
        return take.to_dict()
    except VideoGenerationError as e:
        return _error_response(e)


@app.put("/api/takes/{take_id}/rollback")
async def rollback_take(take_id: str):
    """Rollback Take。"""
    try:
        client = get_client()
        take = client.rollback_take(take_id)
        if take is None:
            raise HTTPException(status_code=404, detail=f"Take not found: {take_id}")
        return take.to_dict()
    except VideoGenerationError as e:
        return _error_response(e)


# ──────────────────────────────────────────────
# 端點：資產 serving（by SHA, 安全）
# ──────────────────────────────────────────────

@app.get("/api/assets/{sha}/video")
async def serve_asset_video(sha: str):
    """透過 SHA-256 安全提供影片資產。"""
    client = get_client()
    path = client.assets.get_asset_path(sha)
    if path is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(str(path), media_type="video/mp4")


@app.get("/api/assets/{sha}/thumbnail")
async def serve_asset_thumbnail(sha: str):
    """透過 SHA-256 提供縮圖。"""
    client = get_client()
    asset = client.assets.get_asset(sha)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    # Check for thumbnail in metadata
    meta = asset.get("metadata", {})
    thumb = meta.get("thumbnail_path")
    if thumb and Path(thumb).exists():
        return FileResponse(thumb, media_type="image/jpeg")
    # Try to find a .thumb.jpg next to the video
    video_path = Path(asset["file_path"])
    thumb_path = video_path.with_suffix(".thumb.jpg")
    if thumb_path.exists():
        return FileResponse(str(thumb_path), media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Thumbnail not found")


@app.get("/api/takes/{take_id}/thumbnail")
async def serve_take_thumbnail(take_id: str):
    """透過 Take ID 提供縮圖。"""
    client = get_client()
    take = client.get_take(take_id)
    if take is None:
        raise HTTPException(status_code=404, detail=f"Take not found: {take_id}")
    if take.thumbnail_path and Path(take.thumbnail_path).exists():
        return FileResponse(take.thumbnail_path, media_type="image/jpeg")
    # Fallback: try .thumb.jpg
    thumb = Path(take.file_path).with_suffix(".thumb.jpg")
    if thumb.exists():
        return FileResponse(str(thumb), media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Thumbnail not found")


@app.get("/api/takes/{take_id}/video")
async def serve_take_video(take_id: str):
    """透過 Take ID 提供影片。"""
    client = get_client()
    take = client.get_take(take_id)
    if take is None:
        raise HTTPException(status_code=404, detail=f"Take not found: {take_id}")
    if not Path(take.file_path).exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    return FileResponse(take.file_path, media_type="video/mp4")


# ──────────────────────────────────────────────
# 端點：時間線與匯出
# ──────────────────────────────────────────────

@app.get("/api/timeline")
async def export_timeline(shot_ids: str | None = Query(None)):
    """匯出時間線。"""
    client = get_client()
    ids = shot_ids.split(",") if shot_ids else None
    return client.export_timeline(ids)


@app.post("/api/timeline/concat")
async def concat_final(req: ConcatRequest):
    """合併 ACTIVE takes 為最終 MP4。"""
    client = get_client()
    path = client.concat_active_takes(req.output_path)
    if path is None:
        return {"error": True, "message": "No active takes or ffmpeg unavailable"}
    return {"output_path": path, "status": "done"}


# ──────────────────────────────────────────────
# 端點：參考圖上傳
# ──────────────────────────────────────────────

@app.post("/api/upload/reference")
async def upload_reference_image(file: UploadFile = File(...)):
    """上傳參考圖片至 workspace/.assets/refs/"""
    import shutil
    refs_dir = Path(getattr(get_client(), 'workspace', '.')) / ASSETS_DIR_NAME / 'refs'
    refs_dir.mkdir(parents=True, exist_ok=True)
    allowed = {'image/jpeg', 'image/png', 'image/webp'}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported type: {file.content_type}. Use JPEG/PNG/WebP.")
    # Validate file size (max 10MB)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    suffix = Path(file.filename).suffix or '.jpg'
    dest = refs_dir / f"ref_{uuid.uuid4().hex[:12]}{suffix}"
    dest.write_bytes(content)
    return {"path": str(dest), "filename": file.filename, "size_bytes": len(content)}


# ──────────────────────────────────────────────
# 端點：分析
# ──────────────────────────────────────────────

@app.get("/api/analytics/cost")
async def get_cost_summary():
    """成本分析總覽。"""
    return get_client().get_cost_summary()


@app.get("/api/analytics/failures")
async def get_failure_stats():
    """失敗統計。"""
    return get_client().get_failure_stats()


@app.get("/api/analytics/events")
async def get_events(event_type: str | None = Query(None), limit: int = Query(100)):
    """事件日誌查詢。"""
    return get_client().get_event_log(event_type, limit)


# ──────────────────────────────────────────────
# 啟動
# ──────────────────────────────────────────────

def main():
    """啟動 FastAPI Server。"""
    import uvicorn
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8765"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()

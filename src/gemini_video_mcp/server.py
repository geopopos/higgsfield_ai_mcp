"""
FastMCP Server — Gemini Video MCP v3.3 — Director Orchestration
=======================================

向 Claude / Antigravity / Cursor 暴露標準 MCP Tools。

工具清單：
  • mcp_gemini_generate_draft      — 720p Lite/Fast 草稿生成（支援音訊 prompt + 參考圖）
  • mcp_gemini_generate_transition — 首尾幀補間轉場（含連續性預檢）
  • mcp_gemini_extend_scene        — 長鏡頭延伸（特徵重錨定，固定 +7s）
  • mcp_gemini_edit_take           — 預留介面（目前回傳 capability error）
  • mcp_gemini_upscale_4k          — 已核准鏡頭的 4K 重渲（非後製 upscale）
  • mcp_gemini_set_take_active     — 將 QA 通過的 Take 設為 ACTIVE
  • mcp_gemini_set_take_qa         — 設定 Take QA 狀態
  • mcp_gemini_rollback_take       — 標記 Take 為 rolled_back（保留 lineage）
  • mcp_gemini_export_timeline     — 匯出 ACTIVE takes 時間線
  • mcp_gemini_concat_final        — 合併 ACTIVE takes 為最終 MP4
  • mcp_gemini_cost_summary       — 成本分析總覽

設計原則：
  • 異步工具 (async def) — Veo long-running operation 為 I/O 密集型
  • Pydantic 模型輸入驗證
  • ToolAnnotations 標註安全性
  • 完整 TakeResult dict 回傳（含 provider/operation_id/thumbnail_path）
  • 標準錯誤碼 (VideoErrorCode)
  • shot_id + sequence_order 支援時間線匯出
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Annotated

# 確保 src 在 path 中
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import FastMCP
try:
    from fastmcp import ToolAnnotations
except ImportError:
    from mcp.types import ToolAnnotations

from .client import (
    GeminiVideoClient,
    TakeRecord,
    TakeResult,
    CostEstimate,
    ContinuityReport,
    VideoErrorCode,
    VideoGenerationError,
    VIDEO_PRICING,
    DEFAULT_USD_TWD_RATE,
    MIN_DURATION_SECONDS,
    MAX_DURATION_SECONDS,
    MAX_CUMULATIVE_EXTEND_SECONDS,
    MAX_REFERENCE_IMAGES,
    EXTENSION_STEP_SECONDS,
)

# ──────────────────────────────────────────────
# 初始化 Client（支援環境變數控制）
# ──────────────────────────────────────────────

def _create_client() -> GeminiVideoClient:
    """從環境變數建立 GeminiVideoClient。"""
    mock = os.getenv("MOCK_MODE", "false").lower() in ("true", "1", "yes")
    workspace = os.getenv("WORKSPACE_DIR", ".")
    rate_str = os.getenv("USD_TWD_RATE")
    rate = float(rate_str) if rate_str else None
    return GeminiVideoClient(
        mock_mode=mock,
        workspace=workspace,
        usd_twd_rate=rate,
    )


# ──────────────────────────────────────────────
# FastMCP Server 實例
# ──────────────────────────────────────────────

mcp: FastMCP = FastMCP("gemini-video")

# 全域 client（lazy init）
_client: GeminiVideoClient | None = None


def get_client() -> GeminiVideoClient:
    """取得或初始化全域 GeminiVideoClient。"""
    global _client
    if _client is None:
        _client = _create_client()
    return _client


# ──────────────────────────────────────────────
# 輔助函數
# ──────────────────────────────────────────────

def _take_result_to_dict(result: TakeResult) -> dict:
    """將 TakeResult 轉為完整 MCP 回傳 dict（v3.3: 包含 provider/operation_id/thumbnail_path）。"""
    return result.to_dict()


def _take_record_to_dict(take: TakeRecord) -> dict:
    """將 TakeRecord 轉為 MCP 回傳 dict。"""
    return take.to_dict()


def _format_error(e: VideoGenerationError) -> dict:
    """格式化錯誤回傳。"""
    return {
        "error": True,
        "error_code": e.code.value,
        "message": e.message,
        "details": e.details,
    }


# ──────────────────────────────────────────────
# MCP Tool: mcp_gemini_generate_draft
# ──────────────────────────────────────────────

@mcp.tool(
    annotations=ToolAnnotations(
        title="⚡ 720p 快速試稿",
        destructiveHint=False,
        openWorldHint=True,
        readOnlyHint=False,
    )
)
async def mcp_gemini_generate_draft(
    prompt: Annotated[str, "場景描述文字 prompt"],
    duration_ms: Annotated[int, "影片時長（整數毫秒，4000/6000/8000）"],
    audio_clip_path: Annotated[str | None, "音訊片段路徑（原生音訊由 Veo 3.1 產生；外部音訊只作節奏分析）"] = None,
    reference_images: Annotated[list[str] | None, "角色/場景參考圖路徑列表（最多 3 張）"] = None,
    aspect_ratio: Annotated[str, "寬高比: 16:9 (橫式) 或 9:16 (直式)"] = "16:9",
    resolution: Annotated[str, "輸出解析度: 720p / 1080p / 4k（v3.0 起不再支援 360p）"] = "720p",
    negative_prompt: Annotated[str | None, "負面提示詞（Omni 不接受獨立 negative_prompt；會併入一般 prompt）"] = None,
    quality: Annotated[str, "品質等級: draft / fast / auto / final / premium"] = "auto",
    shot_id: Annotated[str | None, "分鏡 ID（用於時間線匯出）"] = None,
    sequence_order: Annotated[int, "序列順序（用於時間線排序）"] = 0,
    dialogue_script: Annotated[str | None, "對話腳本（Veo 3.1 原生音訊 prompt）"] = None,
    sfx_cues: Annotated[str | None, "音效提示（例如: door slam, footsteps on gravel）"] = None,
    ambient_audio: Annotated[str | None, "環境音描述（例如: distant traffic, room tone）"] = None,
    music_direction: Annotated[str | None, "音樂方向（例如: tense ambient drone, upbeat pop）"] = None,
) -> dict:
    """
    生成 720p 快速草稿影片（Veo 3.1 Lite/Fast，由 ModelRouter 依 quality 自動選型）。

    v3.3 新增：
    - shot_id / sequence_order 支援時間線匯出
    - dialogue_script / sfx_cues / ambient_audio / music_direction 原生音訊 prompt 欄位
    - 預算閘門：生成前檢查 SESSION_BUDGET_TWD
    - 縮圖自動生成
    """
    try:
        client = get_client()
        result = await asyncio.to_thread(
            client.generate_draft_video,
            prompt=prompt,
            duration_ms=duration_ms,
            audio_clip_path=audio_clip_path,
            reference_images=reference_images,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            negative_prompt=negative_prompt,
            quality=quality,
            shot_id=shot_id,
            sequence_order=sequence_order,
            dialogue_script=dialogue_script,
            sfx_cues=sfx_cues,
            ambient_audio=ambient_audio,
            music_direction=music_direction,
        )
        return _take_result_to_dict(result)
    except VideoGenerationError as e:
        return _format_error(e)
    except Exception as e:
        return _format_error(VideoGenerationError(
            VideoErrorCode.GENERATION_FAILED, f"Unexpected error: {e}"
        ))


# ──────────────────────────────────────────────
# MCP Tool: mcp_gemini_generate_transition
# ──────────────────────────────────────────────

@mcp.tool(
    annotations=ToolAnnotations(
        title="🔄 首尾影格轉場",
        destructiveHint=False,
        openWorldHint=True,
        readOnlyHint=False,
    )
)
async def mcp_gemini_generate_transition(
    start_img_path: Annotated[str, "起始幀圖片路徑"],
    end_img_path: Annotated[str, "結束幀圖片路徑"],
    duration_ms: Annotated[int, "轉場時長（整數毫秒，4000/6000/8000）"],
    prompt: Annotated[str | None, "轉場描述（可選，預設自動生成）"] = None,
    resolution: Annotated[str, "輸出解析度"] = "720p",
    aspect_ratio: Annotated[str, "寬高比"] = "16:9",
    shot_id: Annotated[str | None, "分鏡 ID"] = None,
    sequence_order: Annotated[int, "序列順序"] = 0,
) -> dict:
    """首尾幀補間轉場生成（含連續性預檢 + 預算閘門）。"""
    try:
        client = get_client()
        result = await asyncio.to_thread(
            client.generate_transition_video,
            start_img_path=start_img_path,
            end_img_path=end_img_path,
            duration_ms=duration_ms,
            prompt=prompt,
            resolution=resolution,
            aspect_ratio=aspect_ratio,
            shot_id=shot_id,
            sequence_order=sequence_order,
        )
        return _take_result_to_dict(result)
    except VideoGenerationError as e:
        return _format_error(e)
    except Exception as e:
        return _format_error(VideoGenerationError(
            VideoErrorCode.GENERATION_FAILED, f"Unexpected error: {e}"
        ))


# ──────────────────────────────────────────────
# MCP Tool: mcp_gemini_extend_scene
# ──────────────────────────────────────────────

@mcp.tool(
    annotations=ToolAnnotations(
        title="🔄 延伸場景",
        destructiveHint=False,
        openWorldHint=True,
        readOnlyHint=False,
    )
)
async def mcp_gemini_extend_scene(
    video_ref_path: Annotated[str, "前段影片路徑（必須為已註冊的 Veo 生成影片）"],
    extend_sec: Annotated[int, f"延伸秒數，Veo 3.1 每次操作固定為 {EXTENSION_STEP_SECONDS} 秒"],
    character_anchor_img: Annotated[str | None, "角色錨定參考圖（Master Sheet）"] = None,
    prompt: Annotated[str | None, "延伸描述（可選）"] = None,
    resolution: Annotated[str, "輸出解析度（延伸僅支援 720p）"] = "720p",
    aspect_ratio: Annotated[str, "寬高比"] = "16:9",
    previous_interaction_id: Annotated[str | None, "前一次互動 ID"] = None,
    shot_id: Annotated[str | None, "分鏡 ID"] = None,
    sequence_order: Annotated[int, "序列順序"] = 0,
) -> dict:
    """
    長鏡頭延伸生成。

    v3.3 新增：
    - 來源驗證：必須為已註冊的 Veo 生成影片
    - Extension step 追蹤：最多 20 次，累計 148 秒
    - Veo storage TTL 檢查：影片生成後 2 天內有效
    - 預算閘門
    """
    try:
        client = get_client()
        result = await asyncio.to_thread(
            client.extend_scene_video,
            video_ref_path=video_ref_path,
            extend_sec=extend_sec,
            character_anchor_img=character_anchor_img,
            prompt=prompt,
            resolution=resolution,
            aspect_ratio=aspect_ratio,
            previous_interaction_id=previous_interaction_id,
            shot_id=shot_id,
            sequence_order=sequence_order,
        )
        return _take_result_to_dict(result)
    except VideoGenerationError as e:
        return _format_error(e)
    except Exception as e:
        return _format_error(VideoGenerationError(
            VideoErrorCode.GENERATION_FAILED, f"Unexpected error: {e}"
        ))


# ──────────────────────────────────────────────
# MCP Tool: mcp_gemini_edit_take
# ──────────────────────────────────────────────

@mcp.tool(
    annotations=ToolAnnotations(
        title="💬 Omni 對話式精煉",
        destructiveHint=False,
        openWorldHint=False,
        readOnlyHint=False,
    )
)
async def mcp_gemini_edit_take(
    previous_interaction_id: Annotated[str, "前一次互動的 interaction_id"],
    instruction: Annotated[str, "編輯指令（自然語言）"],
    resolution: Annotated[str | None, "輸出解析度（None = 沿用前次）"] = None,
    aspect_ratio: Annotated[str | None, "寬高比（None = 沿用前次）"] = None,
) -> dict:
    """
    對話式 Take 精煉。使用 Gemini Omni Flash 的 Interactions API stateful editing。
    需要傳入 Omni interaction_id；Veo 3.1 Take 不適用此工具。
    """
    try:
        client = get_client()
        result = await asyncio.to_thread(
            client.edit_take,
            previous_interaction_id=previous_interaction_id,
            instruction=instruction,
            resolution=resolution,
            aspect_ratio=aspect_ratio,
        )
        return _take_result_to_dict(result)
    except VideoGenerationError as e:
        return _format_error(e)
    except Exception as e:
        return _format_error(VideoGenerationError(
            VideoErrorCode.GENERATION_FAILED, f"Unexpected error: {e}"
        ))


# ──────────────────────────────────────────────
# MCP Tool: mcp_gemini_upscale_4k
# ──────────────────────────────────────────────

@mcp.tool(
    annotations=ToolAnnotations(
        title="🚀 4K 升頻",
        destructiveHint=False,
        openWorldHint=True,
        readOnlyHint=False,
    )
)
async def mcp_gemini_upscale_4k(
    take_id: Annotated[str, "要升頻的 Take ID"],
) -> dict:
    """4K 高畫質升頻渲染（含預算閘門檢查）。"""
    try:
        client = get_client()
        result = await asyncio.to_thread(
            client.upscale_video_4k,
            take_id=take_id,
        )
        return _take_result_to_dict(result)
    except VideoGenerationError as e:
        return _format_error(e)
    except Exception as e:
        return _format_error(VideoGenerationError(
            VideoErrorCode.GENERATION_FAILED, f"Unexpected error: {e}"
        ))


# ──────────────────────────────────────────────
# MCP Tools: Take 管理
# ──────────────────────────────────────────────

@mcp.tool(
    annotations=ToolAnnotations(
        title="✅ 設定 Take 為 ACTIVE",
        destructiveHint=False,
        openWorldHint=False,
        readOnlyHint=False,
    )
)
async def mcp_gemini_set_take_active(
    take_id: Annotated[str, "Take ID"],
) -> dict:
    """將指定 Take 設為 ACTIVE（需先通過 QA；同 shot 的其他 ACTIVE take 會被自動降級）。"""
    try:
        client = get_client()
        take = client.set_take_active(take_id)
        if take is None:
            return {"error": True, "error_code": "INTERACTION_NOT_FOUND", "message": f"Take not found: {take_id}"}
        return _take_record_to_dict(take)
    except VideoGenerationError as e:
        return _format_error(e)
    except Exception as e:
        return {"error": True, "error_code": "GENERATION_FAILED", "message": str(e)}


@mcp.tool(
    annotations=ToolAnnotations(
        title="🔍 QA 審查",
        destructiveHint=False,
        openWorldHint=False,
        readOnlyHint=False,
    )
)
async def mcp_gemini_set_take_qa(
    take_id: Annotated[str, "Take ID"],
    qa_state: Annotated[str, "QA 狀態: pending / passed / failed"],
) -> dict:
    """設定 Take 的 QA 狀態。"""
    try:
        client = get_client()
        take = client.set_take_qa(take_id, qa_state)
        if take is None:
            return {"error": True, "error_code": "INTERACTION_NOT_FOUND", "message": f"Take not found: {take_id}"}
        return _take_record_to_dict(take)
    except VideoGenerationError as e:
        return _format_error(e)
    except Exception as e:
        return {"error": True, "error_code": "GENERATION_FAILED", "message": str(e)}


@mcp.tool(annotations=ToolAnnotations(
    title="↩️ Rollback Take",
    destructiveHint=False,
    openWorldHint=False,
    readOnlyHint=False,
))
async def mcp_gemini_rollback_take(take_id: Annotated[str, "Take ID"]) -> dict:
    """將 Take 標記為 rolled_back；保留完整 lineage 與資產。"""
    try:
        take = get_client().rollback_take(take_id)
        if take is None:
            return {"error": True, "error_code": "INTERACTION_NOT_FOUND", "message": f"Take not found: {take_id}"}
        return _take_record_to_dict(take)
    except Exception as e:
        return {"error": True, "error_code": "GENERATION_FAILED", "message": str(e)}


# ──────────────────────────────────────────────
# MCP Tools: 時間線匯出與分析
# ──────────────────────────────────────────────

@mcp.tool(annotations=ToolAnnotations(
    title="📋 匯出時間線",
    destructiveHint=False,
    openWorldHint=False,
    readOnlyHint=True,
))
async def mcp_gemini_export_timeline(
    shot_ids: Annotated[list[str] | None, "指定分鏡 ID 列表（None = 全部）"] = None,
) -> dict:
    """匯出 ACTIVE/final takes 為時間線結構（用於 concat 或 EDL）。"""
    try:
        client = get_client()
        result = await asyncio.to_thread(client.export_timeline, shot_ids)
        return result
    except Exception as e:
        return {"error": True, "error_code": "GENERATION_FAILED", "message": str(e)}


@mcp.tool(annotations=ToolAnnotations(
    title="🎬 合併最終影片",
    destructiveHint=False,
    openWorldHint=False,
    readOnlyHint=False,
))
async def mcp_gemini_concat_final(
    output_path: Annotated[str | None, "輸出檔案路徑（None = 自動產生）"] = None,
) -> dict:
    """合併所有 ACTIVE/final takes 為單一 MP4 檔案。"""
    try:
        client = get_client()
        path = await asyncio.to_thread(client.concat_active_takes, output_path)
        if path is None:
            return {"error": True, "error_code": "GENERATION_FAILED", "message": "No active takes or ffmpeg unavailable"}
        return {"output_path": path, "status": "done"}
    except Exception as e:
        return {"error": True, "error_code": "GENERATION_FAILED", "message": str(e)}


@mcp.tool(annotations=ToolAnnotations(
    title="💰 成本分析",
    destructiveHint=False,
    openWorldHint=False,
    readOnlyHint=True,
))
async def mcp_gemini_cost_summary() -> dict:
    """取得目前 session 的成本總覽（by model、estimated vs billable）。"""
    try:
        client = get_client()
        return await asyncio.to_thread(client.get_cost_summary)
    except Exception as e:
        return {"error": True, "error_code": "GENERATION_FAILED", "message": str(e)}


# ──────────────────────────────────────────────
# MCP Resources
# ──────────────────────────────────────────────

@mcp.resource("gemini-video://takes")
async def list_takes() -> str:
    """列出所有已註冊的 Take 記錄。"""
    client = get_client()
    takes = client.list_takes()
    return json.dumps([_take_record_to_dict(t) for t in takes], indent=2, ensure_ascii=False)


@mcp.resource("gemini-video://takes/{take_id}")
async def get_take_resource(take_id: str) -> str:
    """查詢指定 Take 的詳細記錄。"""
    client = get_client()
    take = client.get_take(take_id)
    if take is None:
        return json.dumps({"error": "Take not found", "take_id": take_id})
    return json.dumps(_take_record_to_dict(take), indent=2, ensure_ascii=False)


@mcp.resource("gemini-video://capabilities")
async def get_capabilities() -> str:
    """列出目前 API 支援的能力。"""
    client = get_client()
    caps = client.get_capabilities()
    return json.dumps(caps, indent=2, ensure_ascii=False)


@mcp.resource("gemini-video://pricing")
async def get_pricing() -> str:
    """列出目前 Provider / Model / Resolution 定價表。"""
    return json.dumps(VIDEO_PRICING, indent=2, ensure_ascii=False)


@mcp.resource("gemini-video://router")
async def get_router_status() -> str:
    """列出 Director Router 的目前模型選擇狀態。"""
    return json.dumps(get_client().get_router_status(), indent=2, ensure_ascii=False)


@mcp.resource("gemini-video://analytics/events")
async def get_events() -> str:
    """查詢最近 100 筆事件日誌。"""
    client = get_client()
    events = client.get_event_log(limit=100)
    return json.dumps(events, indent=2, ensure_ascii=False)


@mcp.resource("gemini-video://analytics/cost")
async def get_cost_analytics() -> str:
    """取得成本分析總覽。"""
    client = get_client()
    return json.dumps(client.get_cost_summary(), indent=2, ensure_ascii=False)


@mcp.resource("gemini-video://analytics/failures")
async def get_failure_analytics() -> str:
    """取得失敗統計。"""
    client = get_client()
    return json.dumps(client.get_failure_stats(), indent=2, ensure_ascii=False)


# ──────────────────────────────────────────────
# Server 入口
# ──────────────────────────────────────────────

def main():
    """啟動 FastMCP Server。"""
    import logging
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8000"))
        mcp.run(transport="http", host=host, port=port)



@mcp.tool(annotations=ToolAnnotations(title="🎬 Director 建立分鏡計畫", destructiveHint=False, openWorldHint=False, readOnlyHint=False))
async def mcp_gemini_director_plan(
    title: Annotated[str, "MV 標題"],
    story: Annotated[str, "故事/敘事主線"],
    scenes: Annotated[list[dict], "場景陣列；每個 scene 可包含 shots 陣列"],
    aspect_ratio: Annotated[str, "16:9 或 9:16"] = "16:9",
    default_duration: Annotated[int, "預設鏡頭秒數"] = 8,
    quality: Annotated[str, "draft / fast / auto / final / premium"] = "auto",
) -> dict:
    """將故事轉成可執行 Shot Plan；只規劃、不花 API 費用。"""
    try:
        return get_client().director_plan(title, story, scenes, aspect_ratio, default_duration, quality)
    except VideoGenerationError as e:
        return _format_error(e)

@mcp.tool(annotations=ToolAnnotations(title="🧪 Director 成本/執行 Dry Run", destructiveHint=False, openWorldHint=False, readOnlyHint=True))
async def mcp_gemini_director_dry_run(plan: Annotated[dict, "director_plan 回傳的 Shot Plan"]) -> dict:
    """在真正生成前驗證鏡頭與預估成本；絕不呼叫影片生成 API。"""
    try:
        return get_client().director_dry_run(plan)
    except VideoGenerationError as e:
        return _format_error(e)


# ──────────────────────────────────────────────
# AI MV Director — upper orchestration layer
# ──────────────────────────────────────────────

@mcp.tool(annotations=ToolAnnotations(title="🎞️ AI MV 建立完整專案", destructiveHint=False, openWorldHint=False, readOnlyHint=False))
async def mcp_ai_mv_create_project(
    title: Annotated[str, "MV 標題"],
    story: Annotated[str, "完整故事/歌詞敘事"],
    scenes: Annotated[list[dict] | None, "可選；未提供時由 deterministic planner 自動拆場景"] = None,
    aspect_ratio: Annotated[str, "16:9 或 9:16"] = "16:9",
    default_duration: Annotated[int, "預設每鏡秒數"] = 8,
    max_budget_twd: Annotated[float, "專案成本上限，新台幣"] = 5000.0,
) -> dict:
    """建立 AI MV Project：Story → Scene → Shot → Model Route；不生成影片。"""
    try:
        from ai_mv_director import MVDirectorEngine, DirectorPolicy
        policy = DirectorPolicy(aspect_ratio=aspect_ratio, default_duration=default_duration, max_budget_twd=max_budget_twd)
        engine = MVDirectorEngine(get_client(), policy)
        return await asyncio.to_thread(engine.create_plan, title, story, scenes)
    except VideoGenerationError as e:
        return _format_error(e)
    except Exception as e:
        return {"error": True, "error_code": "DIRECTOR_FAILED", "message": str(e)}

@mcp.tool(annotations=ToolAnnotations(title="🛡️ AI MV 成本與能力 Gate", destructiveHint=False, openWorldHint=False, readOnlyHint=True))
async def mcp_ai_mv_dry_run(
    project: Annotated[dict, "mcp_ai_mv_create_project 回傳的 project plan"]
) -> dict:
    """執行前 Gate：能力、duration、模型與成本驗證；絕不呼叫生成 API。"""
    try:
        from ai_mv_director import MVDirectorEngine
        return await asyncio.to_thread(MVDirectorEngine(get_client()).dry_run, project)
    except VideoGenerationError as e:
        return _format_error(e)
    except Exception as e:
        return {"error": True, "error_code": "DIRECTOR_FAILED", "message": str(e)}

@mcp.tool(annotations=ToolAnnotations(title="🎬 AI MV 執行核准專案", destructiveHint=False, openWorldHint=True, readOnlyHint=False))
async def mcp_ai_mv_execute_project(
    project: Annotated[dict, "已通過 dry-run 的 project plan"],
    approval_token: Annotated[str, "dry-run 回傳的 approval_token；避免未審核專案直接生成"]
) -> dict:
    """顯式執行已核准 Project；不會因為建立 plan 而自動花費生成預算。"""
    try:
        from ai_mv_director import MVDirectorEngine
        return await asyncio.to_thread(MVDirectorEngine(get_client()).execute, project, approval_token)
    except VideoGenerationError as e:
        return _format_error(e)
    except Exception as e:
        return {"error": True, "error_code": "DIRECTOR_FAILED", "message": str(e)}

if __name__ == "__main__":
    main()

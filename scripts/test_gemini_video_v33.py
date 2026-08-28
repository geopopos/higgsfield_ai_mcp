#!/usr/bin/env python3
"""Gemini Video MCP v3.3 — Comprehensive Test Suite.

Tests:
  1. Draft generation (mock)
  2. Transition (mock)
  3. Extend (mock)
  4. QA + ACTIVE gating
  5. 4K upscale (mock)
  6. Rollback
  7. Duration validation errors
  8. Reference image cap
  9. Budget exceeded
 10. Mock cost = 0 billable
 11. Cost summary analytics
 12. Timeline export
 13. Failure stats
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from gemini_video_mcp.client import (
    GeminiVideoClient,
    VideoGenerationError,
    VideoErrorCode,
    SUPPORTED_DURATIONS,
    CAPABILITIES,
    EXTENSION_STEP_SECONDS, MODEL_OMNI_FLASH,
)


def show(label, value):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    if isinstance(value, dict):
        print(json.dumps(value, indent=2, ensure_ascii=False, default=str))
    elif isinstance(value, list):
        print(json.dumps(value, indent=2, ensure_ascii=False, default=str))
    else:
        print(value)


passed = 0
failed = 0
errors = []


def test(name, func):
    global passed, failed
    try:
        func()
        passed += 1
        print(f"  ✅ {name}")
    except AssertionError as e:
        failed += 1
        errors.append(f"{name}: {e}")
        print(f"  ❌ {name}: {e}")
    except Exception as e:
        failed += 1
        errors.append(f"{name}: {e}")
        print(f"  ❌ {name}: {e}")


def main():
    ap = argparse.ArgumentParser(description="Gemini Video MCP v3.3 Test Suite")
    ap.add_argument("--mock", action="store_true", default=True)
    ap.add_argument("--prompt", default="A cinematic neon city street at night, rain reflections, slow dolly shot")
    args = ap.parse_args()

    test_workspace = str(ROOT / "runtime_test")
    # Clean previous test artifacts
    import shutil
    if Path(test_workspace).exists():
        shutil.rmtree(test_workspace)

    c = GeminiVideoClient(mock_mode=True, workspace=test_workspace)

    # ── System info ──
    show("Router", c.get_router_status())
    show("Capabilities", c.get_capabilities())
    show("Pricing", c.get_pricing())

    prompt = args.prompt

    # ── Test 1: Draft generation ──
    draft_result = None

    def test_draft():
        nonlocal draft_result
        r = c.generate_draft_video(prompt, 8000, resolution="720p", aspect_ratio="16:9",
                                    quality="fast", shot_id="SHOT-001", sequence_order=1,
                                    dialogue_script="Hello world", sfx_cues="door slam")
        show("Draft Result", r.to_dict())
        assert r.is_mock, "Draft should be mock"
        assert r.provider == "mock", f"Provider should be mock, got {r.provider}"
        assert r.cost_estimate.model, "Cost estimate should have a model"
        draft_result = r

    test("Draft generation (mock)", test_draft)

    # ── Test 2: Transition ──
    def test_transition():
        # Create dummy images for transition test
        from PIL import Image
        import numpy as np
        img_dir = Path(test_workspace) / "test_images"
        img_dir.mkdir(parents=True, exist_ok=True)
        start_img = img_dir / "start.png"
        end_img = img_dir / "end.png"
        # Create simple test images
        Image.fromarray(np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)).save(start_img)
        Image.fromarray(np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)).save(end_img)

        r = c.generate_transition_video(str(start_img), str(end_img), 8000,
                                         shot_id="SHOT-002", sequence_order=2)
        show("Transition Result", r.to_dict())
        assert r.is_mock, "Transition should be mock"
        assert r.status == "ready", f"Status should be ready, got {r.status}"
    test("Transition (mock)", test_transition)

    # ── Test 3: Extend ──
    extend_result = None

    def test_extend():
        nonlocal extend_result
        # First generate a draft to extend from
        r = c.generate_draft_video(prompt, 8000, resolution="720p", shot_id="SHOT-003")
        ext = c.extend_scene_video(r.file_path, EXTENSION_STEP_SECONDS, shot_id="SHOT-003",
                                    sequence_order=2)
        show("Extend Result", ext.to_dict())
        assert ext.is_mock, "Extend should be mock"
        extend_result = ext

    test("Extend (mock)", test_extend)

    # ── Test 4: QA + ACTIVE gating ──
    def test_qa_active():
        r = c.generate_draft_video(prompt, 8000, resolution="720p", shot_id="SHOT-004")
        # Should fail to set active without QA
        try:
            c.set_take_active(r.take_id)
            assert False, "Should not allow ACTIVE without QA"
        except VideoGenerationError as e:
            assert e.code == VideoErrorCode.COST_GATE_LOCKED, f"Expected COST_GATE_LOCKED, got {e.code}"

        # Pass QA
        c.set_take_qa(r.take_id, "passed")
        # Now should work
        take = c.set_take_active(r.take_id)
        assert take.status == "active", f"Expected active, got {take.status}"

    test("QA + ACTIVE gating", test_qa_active)

    # ── Test 5: 4K upscale ──
    def test_4k():
        r = c.generate_draft_video(prompt, 8000, resolution="720p", shot_id="SHOT-005")
        c.set_take_qa(r.take_id, "passed")
        c.set_take_active(r.take_id)
        r4 = c.upscale_video_4k(r.take_id)
        show("4K Result", r4.to_dict())
        assert r4.is_mock, "4K should be mock"
        assert r4.cost_estimate.resolution == "4k", f"Expected 4k resolution, got {r4.cost_estimate.resolution}"

    test("4K upscale (mock)", test_4k)

    # ── Test 6: Rollback ──
    def test_rollback():
        r = c.generate_draft_video(prompt, 8000, resolution="720p", shot_id="SHOT-006")
        take = c.rollback_take(r.take_id)
        assert take.status == "rolled_back", f"Expected rolled_back, got {take.status}"
        # Verify it persists
        take2 = c.get_take(r.take_id)
        assert take2.status == "rolled_back", "Rollback should persist"

    test("Rollback", test_rollback)

    # ── Test 7: Duration validation errors ──
    def test_duration_errors():
        # Too short
        try:
            c.generate_draft_video(prompt, 2000, resolution="720p")
            assert False, "Should reject 2s duration"
        except VideoGenerationError as e:
            assert e.code == VideoErrorCode.DURATION_OUT_OF_RANGE, f"Expected DURATION_OUT_OF_RANGE, got {e.code}"

        # Non-standard duration
        try:
            c.generate_draft_video(prompt, 5000, resolution="720p")
            assert False, "Should reject 5s (not in 4/6/8)"
        except VideoGenerationError as e:
            assert e.code == VideoErrorCode.DURATION_OUT_OF_RANGE

        # 1080p requires 8s
        try:
            c.generate_draft_video(prompt, 4000, resolution="1080p")
            assert False, "Should reject 4s for 1080p"
        except VideoGenerationError as e:
            assert e.code == VideoErrorCode.DURATION_OUT_OF_RANGE

    test("Duration validation errors", test_duration_errors)

    # ── Test 8: Reference image cap ──
    def test_ref_cap():
        # Create dummy images
        from PIL import Image
        import numpy as np
        img_dir = Path(test_workspace) / "ref_test"
        img_dir.mkdir(parents=True, exist_ok=True)
        refs = []
        for i in range(5):
            p = img_dir / f"ref_{i}.png"
            Image.fromarray(np.random.randint(0, 255, (128, 128, 3), dtype=np.uint8)).save(p)
            refs.append(str(p))

        # 4+ images should fail
        try:
            c.generate_draft_video(prompt, 8000, reference_images=refs, resolution="720p")
            assert False, "Should reject >3 reference images"
        except VideoGenerationError as e:
            assert e.code == VideoErrorCode.INVALID_INPUT, f"Expected INVALID_INPUT, got {e.code}"

        # 3 images should work
        r = c.generate_draft_video(prompt, 8000, reference_images=refs[:3], resolution="720p")
        assert r.is_mock, "Should generate mock with 3 refs"

    test("Reference image cap", test_ref_cap)

    # ── Test 9: Budget exceeded ──
    def test_budget():
        # Set very low budget and mock mode to avoid GenAI client init
        os.environ["SESSION_BUDGET_TWD"] = "0.01"
        # Use mock=True but manually set mock_mode=False on the cost calc path
        # We can't easily test non-mock budget without a real API key,
        # so we test the budget check logic directly
        from gemini_video_mcp.client import CostCalculator, AssetManager
        import tempfile
        ws = tempfile.mkdtemp()
        calc = CostCalculator()
        assets = AssetManager(ws)
        # Create a fake take with high billable cost
        from gemini_video_mcp.client import TakeRecord
        take = TakeRecord(
            take_id="test_budget", asset_sha256="abc", file_path="/fake.mp4",
            prompt="test", billable_cost_twd=100.0, estimated_cost_twd=100.0,
        )
        assets.register_take(take)
        # Budget check should fail
        session_total = calc.get_session_total_billable(assets)
        assert not calc.check_budget(session_total), "Budget check should fail with 100 TWD > 0.01 cap"
        os.environ["SESSION_BUDGET_TWD"] = "5000"

    test("Budget exceeded", test_budget)


    def test_omni_capabilities():
        caps = c.get_capabilities()[MODEL_OMNI_FLASH]
        assert caps["stateful_editing"] is True
        assert caps["resolutions"] == ["360p", "720p", "1080p", "4k"]
        assert 10 in caps["durations"] and 3 in caps["durations"]
        show("Omni capabilities", caps)
    test("Omni GA capabilities", test_omni_capabilities)
    # ── Test 10: Mock cost = 0 billable ──
    def test_mock_cost():
        r = c.generate_draft_video(prompt, 8000, resolution="720p", shot_id="SHOT-COST")
        take = c.get_take(r.take_id)
        assert take.billable_cost_twd == 0.0, f"Mock billable should be 0, got {take.billable_cost_twd}"
        assert take.estimated_cost_twd > 0.0, f"Estimated cost should be > 0, got {take.estimated_cost_twd}"
        assert take.is_mock == True, "Should be marked as mock"
        assert take.provider == "mock", f"Provider should be mock, got {take.provider}"
        show("Mock Take Cost", {
            "estimated_cost_twd": take.estimated_cost_twd,
            "billable_cost_twd": take.billable_cost_twd,
            "is_mock": take.is_mock,
            "provider": take.provider,
        })

    test("Mock cost = 0 billable", test_mock_cost)

    # ── Test 11: Cost summary analytics ──
    def test_cost_summary():
        summary = c.get_cost_summary()
        show("Cost Summary", summary)
        assert summary["take_count"] > 0, "Should have takes"
        assert summary["total_billable_twd"] == 0.0, f"Mock billable should be 0, got {summary['total_billable_twd']}"
        assert summary["total_estimated_twd"] > 0.0, "Estimated should be > 0"

    test("Cost summary analytics", test_cost_summary)

    # ── Test 12: Timeline export ──
    def test_timeline():
        # Set a take active for timeline
        r = c.generate_draft_video(prompt, 8000, resolution="720p", shot_id="SHOT-TL")
        c.set_take_qa(r.take_id, "passed")
        c.set_take_active(r.take_id)
        timeline = c.export_timeline()
        show("Timeline", timeline)
        assert timeline["take_count"] > 0, "Timeline should have takes"
        assert timeline["total_duration_ms"] > 0, "Timeline should have duration"

    test("Timeline export", test_timeline)

    # ── Test 13: Failure stats ──
    def test_failure_stats():
        stats = c.get_failure_stats()
        show("Failure Stats", stats)
        assert "failed_qa" in stats
        assert "rolled_back" in stats
        assert "total" in stats
        assert stats["total"] > 0, "Should have takes"

    test("Failure stats", test_failure_stats)

    # ── Test 14: Thumbnail generation ──
    def test_thumbnail():
        r = c.generate_draft_video(prompt, 8000, resolution="720p", shot_id="SHOT-THUMB")
        take = c.get_take(r.take_id)
        if take.thumbnail_path:
            assert Path(take.thumbnail_path).exists(), f"Thumbnail should exist at {take.thumbnail_path}"
        # Thumbnail is best-effort; if ffmpeg is available it should exist
        ffmpeg = __import__("shutil").which("ffmpeg")
        if ffmpeg:
            assert take.thumbnail_path is not None, "Thumbnail should be generated when ffmpeg is available"

    test("Thumbnail generation", test_thumbnail)

    # ── Test 15: Extension step tracking ──
    def test_extension_step():
        r = c.generate_draft_video(prompt, 8000, resolution="720p", shot_id="SHOT-EXT")
        take = c.get_take(r.take_id)
        assert take.extension_step == 0, f"Initial extension step should be 0, got {take.extension_step}"
        ext = c.extend_scene_video(r.file_path, EXTENSION_STEP_SECONDS, shot_id="SHOT-EXT")
        ext_take = c.get_take(ext.take_id)
        assert ext_take.extension_step == 1, f"Extension step should be 1, got {ext_take.extension_step}"
        assert ext_take.parent_take_id == r.take_id, "Parent should be the original take"
        # Veo extension returns combined video: original 8s + 7s extension = 15s
        assert ext_take.duration_ms == 15000, f"Combined duration should be 15000ms (8s+7s), got {ext_take.duration_ms}"

    test("Extension step tracking", test_extension_step)

    # ── Test 16: Edit take returns error ──
    def test_edit_take_error():
        try:
            c.edit_take("fake_id", "make it more cinematic")
            assert False, "unknown interaction should fail"
        except VideoGenerationError as e:
            assert e.code == VideoErrorCode.INTERACTION_NOT_FOUND, f"Expected INTERACTION_NOT_FOUND, got {e.code}"

    test("Edit take validates interaction", test_edit_take_error)

    # ── Summary ──
    print(f"\n{'='*60}")
    print(f"  RESULTS: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    if errors:
        print("\nFailures:")
        for e in errors:
            print(f"  - {e}")
    print()

    # Cleanup
    if Path(test_workspace).exists():
        shutil.rmtree(test_workspace, ignore_errors=True)
    budget_ws = test_workspace + "_budget"
    if Path(budget_ws).exists():
        shutil.rmtree(budget_ws, ignore_errors=True)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

# v3.3 director regression tests
def test_director_planner():
    from gemini_video_mcp.client import GeminiVideoClient
    import shutil
    ws = ROOT / "runtime_director_test"
    if ws.exists(): shutil.rmtree(ws)
    c = GeminiVideoClient(mock_mode=True, workspace=str(ws))
    plan = c.director_plan(
        "Neon Rain", "A singer searches for someone in a rainy neon city.",
        [{"scene_id":"SCENE-001","description":"Rainy neon street", "shots":[
            {"camera":"wide","duration":8,"quality":"fast"},
            {"camera":"close_up","duration":8,"quality":"final","resolution":"1080p"}
        ]}], aspect_ratio="16:9")
    assert plan["shot_count"] == 2
    assert len(plan["estimated"]["shots"]) == 2
    dry = c.director_dry_run(plan)
    assert dry["mode"] == "dry_run" and dry["would_execute"] == 2

test("Director planner + dry run", test_director_planner)

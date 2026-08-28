import tempfile
from gemini_video_mcp.client import GeminiVideoClient
from ai_mv_director import MVDirectorEngine, DirectorPolicy

def test_plan_dryrun_execute_guard():
    with tempfile.TemporaryDirectory() as td:
        c=GeminiVideoClient(mock_mode=True, workspace=td)
        e=MVDirectorEngine(c, DirectorPolicy(max_budget_twd=5000, default_duration=8))
        p=e.create_plan("Rain", "A singer leaves the city at night. Dawn arrives.")
        assert p["shots"] and p["estimated_twd"] > 0
        d=e.dry_run(p)
        assert d["gate"]["approved"] is True and d["approval_token"]
        try:
            e.execute(p, "invalid")
            assert False
        except Exception as exc:
            assert "approval_token" in str(exc)
        r=e.execute(p, d["approval_token"])
        assert r["status"] == "completed"
        assert all(s["state"] == "generated" for s in r["shots"])

def test_deterministic_project_id():
    with tempfile.TemporaryDirectory() as td:
        c=GeminiVideoClient(mock_mode=True, workspace=td)
        e=MVDirectorEngine(c)
        a=e.create_plan("Same", "Same story.")
        b=e.create_plan("Same", "Same story.")
        assert a["project_id"] == b["project_id"]

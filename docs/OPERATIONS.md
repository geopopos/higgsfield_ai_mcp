# Operations & Runbook Guide
**Platform:** AI MV Autonomous Directing Platform v4.0

---

## 1. Quick Start Commands

```bash
# 1. Run Complete Platform Test Suite (10 test suites)
python tests/test_ai_mv_director_v2.py

# 2. Run Baseline v3.3 Regression Suite (17 tests)
python scripts/test_gemini_video_v33.py

# 3. Launch FastMCP Director Server
python src/gemini_video_mcp/server.py
```

## 2. Environment Variables
- `GEMINI_API_KEY`: Google GenAI API Key for live Veo 3.1 and Omni 1.1 Flash.
- `SESSION_BUDGET_TWD`: Maximum project budget limit in TWD (default: `5000.0`).
- `MOCK_MODE`: Set to `true` (default) for zero-cost offline development and testing.
- `APP_ENV`: `development`, `testing`, or `production`.

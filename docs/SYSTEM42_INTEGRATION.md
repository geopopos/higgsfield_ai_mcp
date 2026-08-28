# System 4.2 Adapter & Senior Agent Governance
**Version:** `4.0.0`

---

## 1. Adapter Surface
The `src/ai_mv_director/system42/` adapter connects the autonomous director with the System 4.2 framework:
- `CapabilityRegistry`: Dynamic capability queries.
- `DecisionTrace`: Immutable decision rationale logs with machine-readable trace IDs.
- `ExperienceRegistry`: Continuous learning database capturing observed pitfalls and recommended policies.
- `PolicyGate`: Non-destructive verification gate.
- `EvidenceGuard`: Enforces proof before promoting takes to `active`.

---

# MCP API Specification
**Version:** `4.0.0`

## Available Tools

### Upper Layer Orchestration Tools:
- `mcp_ai_mv_create_project(title, story, scenes, ...)`
- `mcp_ai_mv_dry_run(project_dict)`
- `mcp_ai_mv_execute_project(project_dict, approval_token)`

### Execution Layer Video Generation Tools:
- `mcp_gemini_generate_video(prompt, duration_ms, resolution, ...)`
- `mcp_gemini_transition(start_image_path, end_image_path, ...)`
- `mcp_gemini_extend(video_path, extension_seconds, ...)`
- `mcp_gemini_upscale_4k(take_id)`
- `mcp_gemini_set_take_qa(take_id, qa_status, score)`
- `mcp_gemini_set_take_active(take_id)`
- `mcp_gemini_rollback_take(take_id)`
- `mcp_gemini_export_timeline(format)`

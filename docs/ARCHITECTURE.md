# AI MV Director Platform Architecture Specification
**Version:** `4.0.0`
**Protocol:** System 4.2 Autonomous Directing Framework

---

## 1. High-Level Architectural Topology

```text
Upper Orchestration Layer (ai_mv_director)
  ├── Domain Bibles (Character, Scene, Visual, Project)
  ├── Musical Timeline Engine (Audio -> Beats -> Energy -> Cuts)
  ├── Shot Planner 2.0 (8 Classifications + Cinematography)
  ├── Model Router (Deterministic Veo/Omni allocation)
  ├── Cost Governance (BudgetManager + CostGate)
  ├── Resumable Job Queue & Runner (Checkpoints + Retry Policy)
  ├── 10-Layer Continuity Engine (Character, Scene, Motion, Temporal)
  ├── Immutable Take Lineage Graph (DAG) & Hierarchical Rollback
  ├── System 4.2 Adapter (Decisions, Traces, Evidence, Policies)
  └── Structured Observability Logger

Execution & Provider Layer (gemini_video_mcp)
  ├── FastMCP Server & JSON-RPC Endpoints
  ├── VideoProvider Interface (Isolated MockProvider, VeoProvider, OmniProvider)
  ├── SQLite Asset & Take Registry
  └── Timeline Exporter (EDL / JSON / MP4)
```

---

## 2. Core Principles
1. **Deterministic Identity**: Every character, scene, shot, take, asset, and timeline has an immutable UUID or content-derived hash. List indexing is never used for identity.
2. **Gated Execution**: Planning never incurs cost. Video generation requires an explicit cryptographically signed `approval_token` issued by the `CostGate`.
3. **Non-Destructive Take Lineage**: Takes are never deleted; failed or superseded takes are marked `rejected` or `rolled_back` in an immutable DAG.
4. **Provider Isolation**: Mock operations require zero credentials and never touch live APIs. Live operations never silently downgrade to Mock.

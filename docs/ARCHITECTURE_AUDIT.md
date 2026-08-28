# ARCHITECTURE AUDIT REPORT
**Gemini Video MCP + AI MV Director Evolution**
**Baseline Version:** v3.3
**Target Architecture:** Production-grade AI MV Autonomous Directing Platform (v4.0)
**Date:** 2026-08-28

---

## 1. Executive Summary

This forensic audit evaluates the existing `gemini_video_mcp` (v3.3) and `ai_mv_director` (v1.0) codebase. The baseline system provides functional video generation orchestration with a mock engine, capability checks, cost calculation, Take registry, and basic approval tokens.

To evolve this into a **Production-grade AI MV Autonomous Directing Platform**, we identified key architectural bottlenecks and formulated a 20-phase non-destructive evolution plan preserving 100% backward compatibility and test stability.

---

## 2. Dependency & Component Map

```
┌─────────────────────────────────────────────────────────────┐
│                 AI MV Director Upper Layer                  │
│  ┌───────────────────────┐        ┌──────────────────────┐  │
│  │ MVDirectorPlanner     │ ─────▶ │ MVDirectorExecutor   │  │
│  └───────────────────────┘        └──────────────────────┘  │
│             │                                │              │
│             ▼                                ▼              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                MVDirectorEngine                       │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Gemini Video MCP v3.3                       │
│  ┌───────────────────────┐        ┌──────────────────────┐  │
│  │ GeminiVideoClient     │ ─────▶ │ AssetManager (SQLite)│  │
│  └───────────────────────┘        └──────────────────────┘  │
│             │                                │              │
│             ▼                                ▼              │
│  ┌───────────────────────┐        ┌──────────────────────┐  │
│  │ CostCalculator        │        │ ContinuityEngine     │  │
│  └───────────────────────┘        └──────────────────────┘  │
│             │                                │              │
│             ▼                                ▼              │
│  ┌───────────────────────┐        ┌──────────────────────┐  │
│  │ TimelineExporter      │        │ RollbackManager      │  │
│  └───────────────────────┘        └──────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Findings & Forensic Gap Analysis

| Dimension | Baseline State (v3.3) | Target State (Production Platform) | Forensic Finding / Gap |
| :--- | :--- | :--- | :--- |
| **Domain Model** | Simple dictionaries & single `DirectorPlan` dataclass | Immutable multi-entity domain model (`Project`, `Character`, `Scene`, `Shot`, `Take`, `Timeline`, `QA`, `Cost`) | Identity tied to list indices; lacks immutable UUIDs for scenes/props. |
| **Character Bible** | None (ad-hoc prompt strings) | Dedicated `CharacterBible` with wardrobe, acting notes, negative constraints & reference sets | No consistency lock across shots; risk of character drift. |
| **Scene Bible** | Embedded in shot text | Explicit `SceneBible` with environment, lighting, palette & continuity rules | Scene parameters must be repeated manually in every shot prompt. |
| **Music Timeline** | Basic BPM / duration heuristics | Audio-driven timeline engine (`Audio ➔ Beat ➔ Bar ➔ Energy ➔ Cut Candidates ➔ Timeline`) | Missing structured downbeat detection and musical intensity mapping. |
| **Shot Planner** | Linear 3-clause text splitter | Shot Planner 2.0 with 8 shot classifications (`HERO`, `ESTABLISHING`, `PERFORMANCE`, etc.) | Lacks camera trajectory classification and lens/lighting metadata. |
| **Model Router** | Monolithic `select_model()` inside planner | Autonomous, traceable, deterministic `ModelRouter` layer | Model selection rationale is opaque; difficult to audit in production. |
| **Cost Governance** | Static cost calculation & budget cap | Layered `CostEstimator`, `BudgetManager`, and multi-state `CostGate` (`COST_OK`, `COST_WARNING`, `COST_BLOCKED`) | No variance tracking between estimated and actual billable spend. |
| **Job System** | Blocking synchronous execution | Asynchronous resilient `JobQueue` with retry policy, pausing, and checkpoints | Long-running renders block client execution; failure recovery is manual. |
| **Continuity QA** | SSIM/Histogram dual-metric | 10-Layer Continuity Engine (Visual, Character, Wardrobe, Scene, Lighting, Color, Object, Motion, Semantic, Temporal) | Single frame comparison fails to evaluate temporal inertia or facial fidelity. |
| **Take Lineage** | Flat take records with interaction ID | Immutable DAG Take Lineage with bidirectional parent/child tracking | Historical takes cannot be inspected as a genealogical tree. |
| **Rollback** | Per-take status update | Hierarchical Rollback (`rollback_take`, `rollback_shot`, `rollback_scene`, `rollback_project`) | Rolling back a scene requires manual individual take manipulation. |
| **System 4.2** | None | Modular Adapter (`CapabilityRegistry`, `DecisionTrace`, `EvidenceGuard`, `ProjectDNA`) | Upper orchestration lacks integration hooks for System 4.2 senior agents. |
| **Provider Isolation** | Tightly coupled in client mock branches | `VideoProvider` ABC with isolated `MockProvider`, `VeoProvider`, `OmniProvider` | Mock logic is interwoven with live API calls. |
| **Configuration** | Environment variables in `.env` | Tiered `config/` packages (`development`, `testing`, `production`) | No environment profile isolation. |

---

## 4. Remediation & Evolution Principles

1. **Zero Breaking Changes**: All 17 existing v3.3 tests and MCP tools (`mcp_gemini_director_plan`, `mcp_gemini_director_dry_run`, `mcp_ai_mv_create_project`, etc.) must remain 100% green.
2. **Layered Separation**: The `gemini_video_mcp` remains the execution foundation, while `ai_mv_director` expands into a full domain-driven platform.
3. **Traceability**: Every decision (model routing, cost gate check, QA score, rollback) produces a structured audit record with a deterministic `trace_id`.

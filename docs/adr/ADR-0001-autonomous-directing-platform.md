# ADR-0001: Autonomous AI MV Directing Platform Architecture

## Status
Accepted

## Context
The previous v3.3 architecture provided video execution and simple linear scene-to-shot planning. However, full-length music video production requires character continuity, scene lighting inheritance, musical beat alignment, budget governance, resumable job execution, and multi-layer continuity auditing without destructive mutations.

## Decision
1. Introduce a strict domain model layer (`src/ai_mv_director/domain`) with immutable entity IDs and separate Character, Scene, and Visual Bibles.
2. Separate model routing into a standalone `ModelRouter` allocating Veo 3.1 Standard, Fast, Lite, and Gemini Omni 1.1 Flash.
3. Introduce a strict `CostGate` requiring cryptographically signed `approval_token`s before any video generation can be triggered.
4. Implement a 10-layer `ContinuityEngine2` and an immutable DAG `TakeLineageGraph`.
5. Integrate System 4.2 governance through a decoupled `System42Adapter`.

## Consequences
- 100% backward compatibility with all v3.3 tests and MCP tools.
- Complete auditability and rollback safety across project, scene, shot, and take levels.
- Seamless provider isolation between mock test runs and live production execution.

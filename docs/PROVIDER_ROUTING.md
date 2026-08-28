# Intelligent Provider & Model Routing Specification
**Version:** `4.0.0`

---

## 1. Routing Decision Matrix

| Task / Classification | Target Resolution | Recommended Model | Rationale & Capabilities |
| :--- | :--- | :--- | :--- |
| **HERO / Master 4K** | 4K | `veo-3.1-generate-preview` | Highest cinematic texture, 4K rendering, native audio |
| **STANDARD** | 1080p | `veo-3.1-generate-preview` | Broadcast quality, deep character consistency |
| **FAST / Production** | 720p | `veo-3.1-fast-generate-preview` | Optimal balance of rendering speed & cinematic motion |
| **LITE / Budget** | 720p | `veo-3.1-lite-generate-preview` | Low-cost rapid iteration |
| **FIRST / LAST FRAME TRANSITION** | 720p / 1080p | `gemini-omni-1.1-flash` | Dual keyframe interpolation, seamless match cuts |
| **10s SCENE EXTENSION** | 720p / 1080p | `gemini-omni-1.1-flash` | Contextual continuation up to 40s total length |
| **STATEFUL MULTI-TURN EDIT** | 720p | `gemini-omni-1.1-flash` | Conversational modifications with lineage retention |
| **DRAFT 360p** | 360p | `gemini-omni-1.1-flash` | Ultra-low-cost (~$0.03/shot) camera path exploration |

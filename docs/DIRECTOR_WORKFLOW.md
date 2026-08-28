# AI MV Director Complete Workflow Guide
**State Flow:** `PLAN ➔ VALIDATE ➔ DRY_RUN ➔ COST_GATE ➔ APPROVAL ➔ QUEUE ➔ EXECUTE ➔ QA ➔ RETRY / ACCEPT ➔ ACTIVE`

---

## Stage Breakdown

1. **PLAN**:
   - `create_plan(title, story, scenes)`: Analyzes lyrics and story, compiles Character & Scene Bibles, generates Shot Planner 2.0 descriptors.
   - Cost: $0 (0 TWD).

2. **VALIDATE & DRY_RUN**:
   - `dry_run(plan)`: Validates model availability, reference limits, duration bounds, and computes estimated total spend.
   - Verifies against `BudgetManager`.
   - Generates unique `approval_token`.

3. **APPROVAL & COST_GATE**:
   - Enforces `COST_OK`, `COST_WARNING`, or `COST_BLOCKED`.
   - Blocks any execution attempt missing the token.

4. **QUEUE & ASYNC EXECUTE**:
   - Enqueues jobs into `JobQueue`.
   - `JobRunner` executes tasks with automatic exponential backoff and checkpointing.

5. **CONTINUITY QA**:
   - `ContinuityEngine2` audits 10 perceptual layers (Character, Wardrobe, Scene, Lighting, Color, Motion, Temporal).
   - Generates score (0.0 to 1.0) and PASS/FAIL decision.

6. **ACCEPT / ROLLBACK**:
   - Successful takes marked `active` and appended to `Timeline`.
   - Unsatisfactory takes rolled back via `RollbackEngine`.

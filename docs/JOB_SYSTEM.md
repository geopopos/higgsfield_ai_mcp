# Resumable Job System Architecture
**Version:** `4.0.0`

---

## 1. Lifecycle State Machine

```
              ┌───────────────┐
              │    PENDING    │
              └───────┬───────┘
                      │ enqueue()
                      ▼
              ┌───────────────┐
              │    QUEUED     │
              └───────┬───────┘
                      │ execute()
                      ▼
         ┌─────────► RUNNING ─────────┐
         │              │             │
         │ retry()      │             ▼
    ┌────┴─────┐        │         ┌───────────┐
    │ RETRYING │        │         │ COMPLETED │
    └──────────┘        │         └───────────┘
         ▲              │
         │ error        ▼
         └─────────── FAILED
```

## 2. Key Methods
- `JobQueue.enqueue(shot_id, project_id, payload, max_retries=3)`
- `JobRunner.execute_job_sync(job_id, task_fn)`
- `Job.add_checkpoint(step_name, progress, data)`
- `JobQueue.cancel(job_id)`

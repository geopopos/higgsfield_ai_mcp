# 10-Layer Continuity Engine Specification
**Version:** `4.0.0`

---

## Evaluation Layers

1. **Character Layer (Weight: 25%)**: Facial structure, age, hair, expression continuity.
2. **Scene Layer (Weight: 20%)**: Spatial architecture, props, environment consistency.
3. **Motion & Trajectory Layer (Weight: 15%)**: Momentum, speed, camera movement alignment.
4. **Lighting & Contrast Layer (Weight: 10%)**: Key-to-fill ratio, angle, shadow direction.
5. **Color & Palette Layer (Weight: 10%)**: Kodak Vision3 grade, saturation, color balance.
6. **Temporal Layer (Weight: 10%)**: Temporal step smooth decay.
7. **Wardrobe Layer (Weight: 10%)**: Garment colors, texture, costume stability.

---

# Resumable Job System
**Version:** `4.0.0`

## Job States
- `PENDING` ➔ `QUEUED` ➔ `RUNNING` ➔ `COMPLETED`
- `RETRYING` (automatic exponential backoff: 2s, 4s, 8s)
- `PAUSED` / `CANCELLED` / `FAILED`

Every job persists state checkpoints in memory / database to allow seamless resumption after timeouts or transient network faults.

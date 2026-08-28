# Cost Governance & Budget Policy
**Version:** `4.0.0`

---

## 1. Governance Architecture
- `BudgetManager`: Enforces total session caps (default: 5,000 TWD) and records variances between estimated and actual spend.
- `CostGate`: Multi-state gate preventing unauthorized or runaway generation.

## 2. Gate States

```
                 ┌───────────────┐
                 │  Plan Request │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ CostGate Eval │
                 └───────┬───────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
   [ COST_OK ]    [ COST_WARNING ] [ COST_BLOCKED ]
   (Spend < 80%)  (80% <= Spend)   (Spend > Budget)
         │               │               │
         ▼               ▼               ▼
    Issue Token     Issue Token    Block Execution
```

# Portfolio Workbench Data Contract

## Data Root And Inputs

`portfolio_data/` is the only mutable data root. The market cache contains `cni_growth.csv`, `cni_value.csv`, `nasdaq.csv`, `china_bond_composite.csv`, `gold.csv`, and `usdcny.csv`. Nasdaq is converted to unhedged CNY with point-aligned USD/CNY data and at most ten days of forward fill.

Other files are `config_events.jsonl`, `records.jsonl`, `outputs/latest_execution_plan.json`, and `uploads/screenshots/`. The project package owns the CLI; the canonical skill wrapper is only a fallback launcher.

## Asset Keys

| key | 中文名 |
| --- | --- |
| `cni_growth` | A股成长 |
| `cni_value` | A股价值 |
| `nasdaq` | 纳斯达克 |
| `china_bond_composite` | 中证全债 |
| `gold` | 黄金 |
| `cash` | 现金 |
| `non_strategy` | 非策略仓位 |

## Current Strategy

```text
risk_budget_a40_us40_gold20_lw504_p90_bondsink_threshold5
```

- Schema: `portfolio_workbench.execution_plan.v2`.
- Fixed bond base: 0.20.
- Risk contribution targets: `cni_growth=0.20`, `cni_value=0.20`, `nasdaq=0.40`, `gold=0.20`.
- Covariance: `ledoit_wolf`, 504 observations strictly before the check date.
- Long-only risk-asset nominal cap: 0.50 of total portfolio.
- Maximum accepted risk-budget error: 0.005.
- Fallback nominal target: 0.15 / 0.15 / 0.30 / 0.20 / 0.20.
- Active tilt: disabled placeholder.
- Risk control: 63d-only P90 cuts 50%; simultaneous 21d and 63d P90 cuts 100%; released weight goes only to bond; bond cap 0.80.
- Decision gate: max absolute deviation at least 0.05; build month bypasses the gate.
- Execution rounding: 0.01.

These modules remain independently auditable: the risk-budget solver creates the base, the active placeholder leaves it unchanged, and the P90 bond sink creates the exact final target.

## Save Record Payload

Payloads contain `valuation_date`, `total_value`, five `asset_amounts`, `cash_amount`, `non_strategy_amount`, optional `etf_names`, optional screenshot metadata, and `confirmed: true`. Weights are derived from amounts. Never commit real account amounts or screenshot names to the skill repository.

## Latest Execution Plan

The root object exposes strategy/schema IDs, check/data dates, execution status, decision-gate diagnostics, strategy snapshot, market signal, risk-budget specification, actions, residual positions, warnings, and totals.

Each `actions[]` item exposes:

- current and execution amounts, plus `target_amount` / `trade_amount` aliases;
- `risk_budget_base_weight`, `risk_budget_target`, `risk_contribution`, `risk_budget_max_error`, `risk_budget_used_fallback`;
- covariance estimator/lookback and Ledoit-Wolf shrinkage;
- active placeholder fields and `pre_risk_control_weight`;
- 21d/63d high-vol flags, raw/applied cut ratios, volatilities and P90 thresholds;
- raw/applied freed weight, bond capacity scale, exact/rounded/execution targets.

Each `residual_positions[]` item includes the same amount aliases plus `kind_cn`.

If no plan exists, `latest-plan` returns exit 0 with `status: empty`. If the stored `strategy_id` differs from the current strategy, it returns exit 0 with `status: stale_strategy`, both IDs, and the stored plan. A stale plan is not actionable and must be regenerated only after explicit holding confirmation.

## Legacy Events

Historical `baseline` and `subjective_offset` events may remain in append-only logs for audit. Neither changes the current strategy. `save-baseline` is legacy audit compatibility; `save-offset` is not a supported command.

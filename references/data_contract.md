# Portfolio Workbench Data Contract

## Data Root

`portfolio_data/` is the only mutable data root for the skill.

- `data_cache/*.csv`: five asset market caches copied or refreshed for this skill.
- `config_events.jsonl`: append-only historical strategy configuration events.
- `records.jsonl`: append-only holding records.
- `outputs/latest_execution_plan.json`: latest traceable execution plan.
- `uploads/screenshots/`: copied user screenshots.

## CLI Entrypoints

The project package owns the CLI implementation in `portfolio_workbench.cli`.

Use `<project-root>/scripts/portfolio_workbench_tool.py` as the preferred runtime wrapper. The canonical skill also keeps `scripts/portfolio_workbench_tool.py` as a fallback launcher for older checkouts, but callers must pass `--project-root <project-root>` explicitly.

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

Only the five strategy assets are allowed in historical baseline events.

## Current Strategy

Current strategy id:

```text
risk_asset_erc_reward_risk_tilt_bond20_dual_vol90_threshold5
```

Current recommendation logic:

1. Base allocation: fix `china_bond_composite` at `0.20`.
2. Base allocation: allocate the remaining `0.80` across `cni_growth`, `cni_value`, `nasdaq`, and `gold` using a 252-trading-day long-only equal-risk-contribution calculation.
3. Active tilt: apply `reward_risk_tilt` (`proxy_adaptation`) to risk assets only. It uses shifted prices, a 252-trading-day lookback, median 21-trading-day compounded return as reward, zero-below loss as risk, clipped rank/z-score transformation, multiplier bounds, and an 8 percentage-point max active deviation from ERC base.
4. Risk control: apply the dual-window high-volatility control:
   - 63d-only high volatility: half cut.
   - 21d and 63d high volatility together: full cut.
5. Risk control: redistribute freed weight by inverse 63d volatility to assets without a risk cut.
6. Round execution targets to 1% steps only after checking the rebalance threshold.

The three modules must stay independently testable:

- ERC base must not apply active tilt or risk cuts.
- Active tilt must consume ERC base and produce `active_tilt_weight_before_risk`.
- Risk control must consume `active_tilt_weight_before_risk` and produce the final exact target.

## Config Events

Historical baseline event:

```json
{
  "kind": "baseline",
  "saved_at": "2099-01-01T10:00:00",
  "baseline": {
    "cni_growth": 0.15,
    "cni_value": 0.15,
    "nasdaq": 0.30,
    "china_bond_composite": 0.20,
    "gold": 0.20
  }
}
```

Programmatic active tilt is not stored as a config event. It is recomputed from market data and appears in `market_signal`, `recommended_allocation`, saved record strategy snapshots, and execution plan actions.

Historical `subjective_offset` events may exist in old append-only logs, but current code must ignore them. They are not strategy state, not a supported CLI command, and not a recommendation input.

## Save Record Payload

The example below uses synthetic placeholder values only. Do not commit real account amounts or screenshot filenames to this repository.

```json
{
  "valuation_date": "2099-01-01",
  "total_value": 100000.00,
  "asset_amounts": {
    "cni_growth": 10000.00,
    "cni_value": 15000.00,
    "nasdaq": 25000.00,
    "china_bond_composite": 20000.00,
    "gold": 15000.00
  },
  "cash_amount": 15000.00,
  "non_strategy_amount": 0,
  "etf_names": {
    "nasdaq": "标普500ETF华夏",
    "china_bond_composite": "易方达新综债LOF",
    "cni_value": "价值ETF易方达",
    "gold": "黄金ETF华夏"
  },
  "screenshot_path": "/absolute/path/to/PLACEHOLDER_SCREENSHOT.JPG",
  "source_id": "PLACEHOLDER_SCREENSHOT.JPG",
  "confirmed": true
}
```

Weights are never accepted from the user. They are calculated from amounts divided by total assets.

## Latest Execution Plan

When `outputs/latest_execution_plan.json` exists, `latest-plan` returns that JSON object.

Each `actions[]` item includes:

- `current_amount`
- `execution_target_amount`
- `execution_trade_amount`
- `target_amount` as an alias of `execution_target_amount`
- `trade_amount` as an alias of `execution_trade_amount`
- `erc_base_weight`
- `active_tilt_id`
- `active_tilt_fidelity_level`
- `active_tilt_weight_before_risk`
- `active_tilt_delta`
- `pre_risk_control_weight`
- `high_vol_21d`
- `high_vol_63d`
- `risk_cut_ratio`, where `0.5` means a 63d-only high-volatility half cut and `1.0` means both 21d and 63d high-volatility signals triggered a full cut

Each `residual_positions[]` item includes the same amount fields plus `kind_cn`.

When no latest plan exists yet, `latest-plan` returns exit 0 with:

```json
{
  "status": "empty",
  "message": "暂无最新执行计划",
  "path": "/absolute/path/to/portfolio_data/outputs/latest_execution_plan.json"
}
```

When a stored latest plan exists but its `strategy_id` differs from the current strategy, `latest-plan` returns exit 0 with:

```json
{
  "status": "stale_strategy",
  "message": "最新执行计划来自旧策略，请在确认最新持仓后重新保存记录生成新计划。",
  "current_strategy_id": "risk_asset_erc_reward_risk_tilt_bond20_dual_vol90_threshold5",
  "stored_strategy_id": "risk_asset_erc_bond20_dual_vol90_threshold5",
  "stored_plan": {}
}
```

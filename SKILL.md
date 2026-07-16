---
name: portfolio-workbench
description: Use this skill when the user wants to run the portfolio rebalance workbench inside Codex, including A40/US40/gold20 risk-budget summaries, P90 risk controls, holding screenshot confirmation, rebalance guidance, JSON/JSONL records, and history.
---

# Portfolio Workbench

## Overview

This skill runs the portfolio rebalance workbench as a Codex-native interaction. Always use the project package `portfolio_workbench` as the execution source. Do not reimplement allocation math in the prompt, do not use the retired web UI, and do not import code or runtime files from `portfolio-dev/`.

## Startup Flow

1. Locate the investment project root and read the nearest `AGENTS.md`.
2. Run `<project-root>/scripts/portfolio_workbench_tool.py --project-root <project-root> summary`. If the project wrapper is absent in an older checkout, use `<this-skill-dir>/scripts/portfolio_workbench_tool.py` and still pass the project root explicitly.
3. Present the returned `startup_report_sections` in their declared order: latest holding record, latest recommended allocation, risk warning, current strategy, then market status.
4. If market refresh fails but the local six-file cache is usable, show the exact refresh error first and ask whether to continue with local cache. If `request_user_input` is available, offer `继续使用本地缓存 (Recommended)` and `中止本轮`. If no usable cache exists, stop and explain the blocker.
5. After any cache decision, present the two menu tabs and their returned options. Prefer native `request_user_input` cards when available.

The expected menu structure is:

- `组合操作`: `持仓截图上传 & 调仓建议生成 (Recommended)`, `查看策略模块参数`, `查看风险预算状态`
- `信息查询`: `查看配置历史与数据状态`, `查看历史持仓记录`, `查看最新执行计划`

## Data Rules

All mutable skill data stays under `portfolio_data/`:

- `data_cache/*.csv`: the five asset caches plus `usdcny.csv`.
- `records.jsonl`: append-only holding records and execution snapshots.
- `config_events.jsonl`: append-only legacy configuration history; it is not a current recommendation input.
- `outputs/latest_execution_plan.json`: latest actionable workbench plan.
- `uploads/screenshots/`: copied holding screenshots.

Network refresh writes to a temporary directory and copies the cache only after all six files validate. Nasdaq must use the unhedged CNY series `Nasdaq USD close * USD/CNY`; never fall back silently to raw USD.

## Holding Screenshot Flow

When the user chooses the holding-screenshot operation:

1. Ask for the latest screenshot if it is not attached.
2. Extract valuation date, total assets, five strategy-asset amounts, cash, non-strategy positions, ETF names, and recognition notes. Ask when a material field is unreadable.
3. Confirm the actual Nasdaq/QDII instrument before assigning overseas equity. Do not map an S&P 500 fund to Nasdaq without explicit approval. Map `成长ETF易方达` to A股成长, `价值ETF易方达` to A股价值, `易方达新综债LOF` to 中证全债, and `黄金9999` or a confirmed domestic gold ETF to 黄金. A missing A股成长 position may be confirmed as zero.
4. Show one confirmation table with `资产类别`, `ETF名称`, `实际金额 CNY`, `当前权重 %`, `识别备注`.
5. Never accept user-entered weights; calculate weights from amounts divided by total assets.
6. Save only after explicit confirmation using `save-record --payload <payload-json>`.

The saved record must include the copied screenshot path, amounts, computed weights, current strategy snapshot, market signal, and generated execution plan.

## Strategy Logic

Current strategy ID:

```text
risk_budget_a40_us40_gold20_lw504_p90_bondsink_threshold5
```

The recommendation pipeline has three independent modules:

1. Risk-budget base
   - Hold a fixed 20% nominal base in `china_bond_composite`.
   - Allocate the other 80% across A股成长, A股价值, 纳斯达克, and 黄金 with target risk contributions 20% / 20% / 40% / 20%. This is A股40% / 美股40% / 黄金20% of the risk sleeve, not nominal capital weights.
   - Use the 504 observations strictly before the monthly check date and a Ledoit-Wolf shrinkage covariance matrix.
   - Solve long-only weights with each risk asset capped at 50% of the total portfolio and require maximum risk-budget error no greater than 0.005.
   - If the history is insufficient or the solver fails validation, fall back to nominal weights 15% / 15% / 30% / 20% / 20%.
2. Active tilt
   - `active_tilt_placeholder` is explicit but disabled.
   - It must not alter the risk-budget base: `active_tilt_weight_before_risk = risk_budget_base_weight`, `active_tilt_delta = 0`.
3. P90 bond-sink risk control
   - For each risk asset, compare current 21-day and 63-day annualized volatility with its own expanding point-in-time P90 history.
   - 63d only: cut 50%. Both 21d and 63d: cut 100%. 21d only: no cut.
   - Transfer all released weight only to `china_bond_composite`; do not redistribute it to another risk asset.
   - Cap the bond weight at 80%. If capacity is insufficient, scale all triggered cuts proportionally.

All point-in-time inputs must be known strictly before the check date. Historical `subjective_offset` events remain audit-only and must not enter current state, summaries, recommendations, or plans.

## Risk And Guidance Rules

- Expose the risk-budget inputs and result: strategy ID, asset risk targets, covariance estimator/lookback, Ledoit-Wolf shrinkage, nominal base weights, realized risk contributions, maximum error, and fallback flag.
- Expose module separation: `risk_budget_base_weight`, active-tilt fields, `pre_risk_control_weight`, raw/applied cut ratios, 21d/63d volatility and P90 thresholds, freed weight, bond capacity scale, and final exact target.
- Check monthly on the first common trading day. Ordinary months rebalance the whole portfolio only when at least one asset's absolute deviation from the model target is 5% or more. A build month ignores this gate.
- Round executable targets to 1% steps only after applying the 5% decision gate.
- Warnings are advisory: every warning has `blocking: false`; they may produce `ready_with_warnings` but never `execution_blocked = true`.
- Display residual holdings as `现金` and `非策略仓位`.
- Do not show a net-worth curve.

## Commands

Preferred commands from the project root:

```bash
"<project-root>/.venv/bin/python" "<project-root>/scripts/portfolio_workbench_tool.py" --project-root "<project-root>" summary
"<project-root>/.venv/bin/python" "<project-root>/scripts/portfolio_workbench_tool.py" --project-root "<project-root>" history
"<project-root>/.venv/bin/python" "<project-root>/scripts/portfolio_workbench_tool.py" --project-root "<project-root>" latest-plan
"<project-root>/.venv/bin/python" "<project-root>/scripts/portfolio_workbench_tool.py" --project-root "<project-root>" save-record --payload "<payload-json>"
"<project-root>/.venv/bin/python" "<project-root>/scripts/portfolio_workbench_tool.py" --project-root "<project-root>" save-baseline --payload "<payload-json>"  # legacy audit only
```

Use UTF-8 JSON payloads and prefer temporary payload files under `/tmp`. Global options may appear before or after the subcommand, but documentation should keep them before it. The wrapper may re-exec into the project `.venv`.

`latest-plan` returns exit 0 when empty. If the stored plan has a different strategy ID, it returns `stale_strategy`; do not present that plan as current and do not regenerate one until the user confirms current holdings.

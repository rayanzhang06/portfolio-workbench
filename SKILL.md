---
name: portfolio-workbench
description: Use this skill to generate the current portfolio-dev daily rebalance signal or turn a confirmed holding screenshot into concrete CNY rebalance amounts.
---

# Portfolio Workbench

## Purpose

This skill has exactly two user-facing functions:

1. Generate the current daily rebalance signal.
2. Convert a confirmed holding screenshot into concrete rebalance amounts.

Always use the project package `portfolio_workbench` as the execution source. Do not reimplement strategy math in the prompt, do not use the retired web UI, and do not import code or runtime files from `portfolio-dev/`.

## Daily Signal Flow

1. Locate the investment project root and read the nearest `AGENTS.md`.
2. Run:

```bash
"<project-root>/.venv/bin/python" "<project-root>/scripts/portfolio_workbench_tool.py" --project-root "<project-root>" signal
```

3. Present `market_refresh.message` first when refresh fails.
4. A failed refresh with usable cache returns `status=cache_confirmation_required` and does not write a signal. Ask whether to continue. Prefer `继续使用本地缓存 (Recommended)` and `中止本轮` when `request_user_input` is available. After confirmation, rerun the same command with `--no-refresh`.
5. Present only the actionable state:
   - data end and monthly check date;
   - insurance state and 504-day rolling drawdown;
   - whether a trade is required and why;
   - five assets' current, exact target, execution target, and buy/sell direction;
   - P90 or insurance warnings when present.

`signal` writes `portfolio_data/outputs/latest_signal.json`. It does not create or change a holding record.

## Holding Screenshot Flow

1. Ask for the latest screenshot when none is attached.
2. Extract valuation date, total assets, the five strategy-asset amounts, cash, non-strategy positions, ETF names, and recognition notes. Ask when a material field is unreadable.
3. Confirm the actual Nasdaq/QDII instrument before assigning overseas equity. Do not map an S&P 500 fund to Nasdaq without explicit approval.
4. Default mappings:
   - `成长ETF易方达` → `cni_growth`
   - `价值ETF易方达` → `cni_value`
   - confirmed Nasdaq/QDII fund → `nasdaq`
   - `易方达新综债LOF` → `china_bond_composite`
   - `黄金9999` or confirmed domestic gold ETF → `gold`
5. Show one confirmation table with `资产类别`, `ETF名称`, `实际金额 CNY`, `当前权重 %`, `识别备注`.
6. Calculate weights from amounts divided by total assets. Never accept user-entered weights.
7. Save and generate amounts only after explicit confirmation. Write the confirmed values to a UTF-8 JSON payload and run:

```bash
"<project-root>/.venv/bin/python" "<project-root>/scripts/portfolio_workbench_tool.py" --project-root "<project-root>" rebalance --payload "/tmp/holding-payload.json"
```

8. Present each asset's current amount, target amount, buy/sell amount, and ETF name. Show cash and non-strategy residuals separately.

If `rebalance` returns `status=cache_confirmation_required`, do not save or present an amount plan. Show the exact refresh error, obtain cache confirmation, then rerun with the same payload plus `--no-refresh`.

The confirmed flow appends `portfolio_data/records.jsonl`, copies the screenshot under `portfolio_data/uploads/screenshots/`, and writes both `latest_signal.json` and `latest_execution_plan.json`.

## Current Strategy

Strategy ID:

```text
equity_rb25_25_50_bond15_gold10_lw504_p90any_dd10r504_c2_threshold5
```

The workbench mirrors the current `portfolio-dev/equal5_vol90` contract but runs independently from `portfolio_data/data_cache/`.

### 1. Equity risk-budget base

- Monthly check: first common trading day, using only observations strictly before the check date.
- Fixed nominal base: bonds 15%, gold 10%.
- Gold is outside covariance, risk budgeting, and P90.
- The 75% equity sleeve targets risk contributions 25% / 25% / 50% for A股成长 / A股价值 / 纳斯达克.
- Covariance: 504 observations and Ledoit-Wolf shrinkage.
- Solver: long-only SLSQP, each equity capped at 50% of total capital, maximum risk-budget error 0.5%.
- Fallback: 18.75% / 18.75% / 37.5% / 15% / 10%.

### 2. P90 bond sink

- Compare each equity's point-in-time 21-day and 63-day annualized volatility with the corresponding prior rolling P90 history.
- Either window alone: cut that equity 50%.
- Both windows: cut that equity 100%.
- Released weight goes only to bonds, capped at 80%; scale cuts proportionally when capacity is insufficient.
- Bonds and gold never enter this layer.

### 3. Portfolio insurance

- Reference: this strategy's own model NAV, not actual account NAV and not a shadow portfolio.
- Drawdown peak: highest close in the latest 504 trading days.
- Enter defense after two consecutive closes at or below −10%; exit after two consecutive closes at or above −10%; trade at the next close.
- Defense target: bonds 80%, gold 10%, equities 10% allocated in proportion to the current P90-normal equity target.
- State changes force execution.

### Execution

- Ordinary rebalance: at least one asset differs from the effective target by 5 percentage points or more.
- Build month and insurance state changes bypass the ordinary gate.
- Executable targets are rounded to 1% steps and corrected to 100%.
- Model NAV applies 0.0001 to buy notional and 0.0001 to sell notional.

## Data Contract

Mutable workbench data stays under `portfolio_data/`:

- `data_cache/*.csv`: five asset caches plus `usdcny.csv`.
- `records.jsonl`: confirmed holding snapshots and their amount plans.
- `outputs/latest_signal.json`: latest holdings-aware daily signal.
- `outputs/latest_execution_plan.json`: latest confirmed screenshot amount plan.
- `uploads/screenshots/`: copied confirmed screenshots.

Nasdaq must use the unhedged CNY series `Nasdaq USD close × USD/CNY`; never fall back silently to raw USD.

Historical `config_events.jsonl` may remain on disk as inert audit data. It is not read by the current workbench and there is no command for changing strategy parameters.

## Safety And Boundaries

- Keep the screenshot confirmation gate.
- Do not invent unreadable amounts, dates, or ETF mappings.
- Do not present a stale prior amount plan as current.
- Warnings are advisory; validation failure stops generation.
- Do not show a net-worth curve.
- Do not expose retired menus, parameter editors, historical strategy variants, or inactive modules.

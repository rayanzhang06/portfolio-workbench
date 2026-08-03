---
name: portfolio-workbench
description: Use this skill to generate the current portfolio-workbench daily rebalance signal or turn a confirmed holding screenshot into concrete CNY rebalance amounts. When no new screenshot is attached, default to the most recent confirmed uploaded holding screenshot.
---

# Portfolio Workbench

## Purpose

This skill has exactly two user-facing functions:

1. Generate the current daily rebalance signal.
2. Convert a confirmed holding screenshot into concrete rebalance amounts.

Always use the project package `portfolio_workbench` as the execution source. Do not reimplement strategy math in the prompt, do not use the retired web UI, and do not import code or runtime files from `portfolio-dev/`.

## NautilusTrader Authority Gate

This gate has highest priority over every flow below.

1. Read `<project-root>/strategy_channels.json` before running `signal` or `rebalance`.
2. Continue only when the active `production` channel declares `status=active`, `framework.name=NautilusTrader`, `framework.version=1.230.0`, `framework.runtime=BacktestNode+ParquetDataCatalog`, and a `run_manifest_field`.
3. Production rev4 is currently `frozen_legacy_no_new_signals`; rev5 is staged but not approved. While that is true, do not call the legacy signal path, do not display its cached signal, and do not calculate an amount plan. Report that production is intentionally frozen pending explicit rev5 promotion approval.
4. After an approved Nautilus production run writes `latest_signal.json`, run:

```bash
"<project-root>/.venv/bin/python" "<project-root>/scripts/verify_nautilus_authority.py" --project-root "<project-root>" --artifact "<project-root>/portfolio_data/outputs/latest_signal.json" --artifact-channel production
```

5. Show or adapt the signal only when the validator returns `status=passed`. The signal's `portfolio.nautilus_run.v1` must bind the production release, Nautilus version, input/calendar/catalog/config digests, reference run, and event/fill/position/result digests. A screenshot or confirmed holding may change only the account amount plan, never that signal or its run manifest.
6. After rev5 promotion, amount adaptation must call the release-declared `portfolio_workbench.nautilus_account_adapter:build_execution_plan` with the verified signal path and one confirmed snapshot. Do not call legacy `PortfolioWorkbench.daily_signal` or enable its migration-oracle test path.

## Default Holding Source

Resolve the actual-account holding source in this order:

1. A holding screenshot attached in the current request. A new attachment always overrides saved history and must go through the confirmation flow below.
2. Otherwise, the most recent confirmed holding record in `portfolio_data/records.jsonl` and its saved screenshot under `portfolio_data/uploads/screenshots/`. “Most recent” means the last valid appended record, not the file modification time.
3. Ask for a new screenshot only when neither source is available or the saved record/screenshot is invalid.

Reusing the most recent confirmed upload does not require OCR or a second confirmation and must not append a duplicate record. Run `signal`; Workbench will use that confirmed snapshot to supersede `latest_execution_plan.json` with the new strategy decision. Identify the reused screenshot source and valuation date in the response so the user can notice if it is stale.

## Daily Signal Flow

1. Locate the investment project root and read the nearest `AGENTS.md`.
2. Pass `NautilusTrader Authority Gate`, then run:

```bash
"<project-root>/.venv/bin/python" "<project-root>/scripts/portfolio_workbench_tool.py" --project-root "<project-root>" signal
```

3. Present `market_refresh.message` first when refresh fails.
4. A failed refresh with usable cache returns `status=cache_confirmation_required` and does not write a signal. Ask whether to continue. Prefer `继续使用本地缓存 (Recommended)` and `中止本轮` when `request_user_input` is available. After confirmation, rerun the same command with `--no-refresh`.
5. Present only the actionable state:
   - data end and monthly check date;
   - insurance state, uninsured-reference NAV drawdown, and whether the episode peak is locked;
   - the shadow strategy's `TRADE` / `HOLD` action and reason;
   - five assets' shadow pre-trade weight, exact target, shadow post-trade weight, and direction;
   - when the default confirmed upload exists, its screenshot source and valuation date, the separate account `TRADE` / `HOLD` action, and the five concrete CNY orders from the regenerated plan;
   - P90 or insurance warnings when present.

`signal` writes the account-independent decision to `portfolio_data/outputs/latest_signal.json`. It does not create or change a holding record. When a confirmed holding already exists, it also supersedes `latest_execution_plan.json` with a plan that references the new decision and that same confirmed snapshot; present that plan only when its `decision_ref.decision_id` matches the new signal. Actual holdings must never feed back into the strategy signal.

## Holding Screenshot Flow

1. Apply `Default Holding Source`. If the most recent confirmed upload is reused, skip OCR and confirmation and use the account plan regenerated by `signal`; continue the remaining steps only for a new attachment.
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
9. Report `strategy_action` and `account_action` separately. The actual account may need `TRADE` while the shadow strategy says `HOLD`.

If `rebalance` returns `status=cache_confirmation_required`, do not save or present an amount plan. Show the exact refresh error, obtain cache confirmation, then rerun with the same payload plus `--no-refresh`.

The confirmed flow appends `portfolio_data/records.jsonl`, copies the screenshot under `portfolio_data/uploads/screenshots/`, and writes both `latest_signal.json` and `latest_execution_plan.json`.

## Current Strategy

Strategy ID:

```text
equity_rb25_25_50_bond15_gold10_lw504_p90any_refnav_dd15lock_c2_bond90gold10_threshold5
```

Production revision: `4`.

Production status: frozen; no new authoritative signals.

Staged production candidate: revision `5`, same strategy ID, NautilusTrader `1.230.0`. It is not production until the release gates pass and the user explicitly approves promotion.

The canonical skill and the project package `portfolio_workbench` are the production channel. The legacy rev4 path is frozen during migration. `portfolio-dev` and staged rev5 are separate candidate/test channels; their outputs are never user-facing production instructions until an explicit promotion updates Workbench, this skill, and the production revision.

The returned production `strategy_id` must equal the ID above. If Workbench, this file, or the production entry in `strategy_channels.json` disagree, stop and report the mismatch. Do not substitute a newer dev candidate for the production strategy.

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

- Reference: a separate continuous shadow NAV that always runs the strategy without F; it never reads the protected NAV, actual account NAV, or screenshot holdings.
- Before the first F entry in an episode, the peak is the uninsured-reference NAV's highest close in the latest 504 trading days. The peak is frozen on first entry.
- Exiting F does not end the episode. Re-entry continues to use the same frozen peak until the uninsured-reference NAV recovers that peak.
- Enter defense after two consecutive closes at or below −15%; exit after two consecutive closes at or above −15%; trade at the next close.
- Defense target: bonds 90%, gold 10%, equities 0%.
- State changes force execution.

### Execution

- Initialize the shadow portfolio once from 100% cash at the first valid replay event, then preserve that continuous path.
- Ordinary monthly rebalance: at least one shadow position differs from the effective target by 5 percentage points or more.
- Initial shadow build and insurance state changes bypass the ordinary gate.
- Executable targets are rounded to 1% steps and corrected to 100%.
- Model NAV applies 0.0001 to buy notional and 0.0001 to sell notional.

## Data Contract

Mutable workbench data stays under `portfolio_data/`:

- `data_cache/*.csv`: five asset caches plus `usdcny.csv`.
- `records.jsonl`: confirmed holding snapshots and their amount plans.
- `outputs/latest_signal.json`: latest account-independent shadow-strategy decision, including its normalized decision identity.
- `outputs/latest_execution_plan.json`: latest account action, referencing one strategy decision and one confirmed holding snapshot.
- `uploads/screenshots/`: copied confirmed screenshots.

Nasdaq must use the unhedged CNY series `Nasdaq USD close × USD/CNY`; never fall back silently to raw USD.

Historical `config_events.jsonl` may remain on disk as inert audit data. It is not read by the current workbench and there is no command for changing strategy parameters.

## Safety And Boundaries

- Keep the screenshot confirmation gate.
- Do not invent unreadable amounts, dates, or ETF mappings.
- Do not present a stale prior amount plan as current.
- Warnings are advisory; validation failure stops generation.
- A missing, stale, mismatched, or non-Nautilus run manifest is a blocking validation failure.
- Do not show a net-worth curve.
- Do not expose retired menus, parameter editors, historical strategy variants, or inactive modules.

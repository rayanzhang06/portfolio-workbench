---
name: portfolio-workbench
description: Use this skill whenever the user asks for the current production portfolio signal, a scheduled portfolio update, current actual-account holdings, or concrete CNY rebalance amounts. Keep signal mode account-independent. In account mode, read only the Investment Ledger “华宝” tab through authenticated Chrome DOM control (`chrome:control-chrome` in Codex or Hermes native browser tools attached to a dedicated CDP Chrome profile), require current and internally consistent data, and use a user-confirmed screenshot as the only fallback.
---

# Portfolio Workbench

## Purpose

This skill has exactly two user-facing functions:

1. Signal Mode: generate and validate the current account-independent strategy signal.
2. Account Mode: convert explicitly confirmed actual-account holdings into concrete rebalance amounts.

Always use the project package `portfolio_workbench` as the execution source. Do not reimplement strategy math in the prompt, do not use the retired Workbench web UI, and do not import code or runtime files from `portfolio-dev/`. The external Investment Ledger page below is a read-only account-data source, not a strategy runtime.

The rev12 release directory is immutable. Its production workbench natively prevents Signal Mode from reading account history and makes Account Mode consume the already verified signal. The canonical script calls this frozen release directly and must never change or replay the Nautilus strategy path.

## NautilusTrader Authority Gate

This gate has highest priority over every flow below.

1. Read `<project-root>/strategy_channels.json` before running `signal` or `rebalance`.
2. Continue only when the active `production` channel declares `status=active`, `framework.name=NautilusTrader`, `framework.version=1.230.0`, `framework.runtime=BacktestNode+ParquetDataCatalog`, and a `run_manifest_field`.
3. Production is active at rev12. Continue only when `strategy_channels.json` points to the exact self-contained rev12 release. Rev11 and rev4 are rollback-only and their cached outputs must never be displayed as current.
4. After the production run writes `latest_signal.json`, run:

```bash
"<project-root>/.venv/bin/python" "<project-root>/scripts/verify_nautilus_authority_v2.py" --project-root "<project-root>" --artifact "<project-root>/portfolio_data/outputs/latest_signal.json" --artifact-channel production
```

5. Show or adapt the signal only when the validator returns `status=passed`. The signal's `portfolio.nautilus_run.v1` must bind the production release, Nautilus version, input/calendar/catalog/config digests, reference run, and event/fill/position/result digests. A screenshot or confirmed holding may change only the account amount plan, never that signal or its run manifest.
6. Amount adaptation must call `portfolio_workbench.nautilus_production_rev12.account_adapter:build_execution_plan` with the verified signal path and one confirmed snapshot. Do not call legacy `PortfolioWorkbench.daily_signal` or enable its migration-oracle test path.

## Account Holding Source

Use this section only in Account Mode. Signal Mode must not open Investment Ledger or read any actual-account source.

1. Use authenticated Chrome DOM control as the primary source after confirming that no dedicated Investment Ledger connector or official API is available:
   - In Codex, read and follow `chrome:control-chrome`, then use its DOM or Playwright APIs against the user's logged-in Chrome session.
   - In Hermes, use the built-in `browser` toolset attached through `browser.cdp_url` to the dedicated headed Hermes Chrome profile. Require callable `browser_navigate`, `browser_snapshot`, `browser_click`, and `browser_console`; do not require Codex's `node_repl` or `browser-client.mjs`.
   - Installed plugin or skill files alone do not prove runtime capability. Continue only when the current session exposes the required adapter tools and can reach the configured browser.
   Open a new controlled tab to `https://tzzb.10jqka.com.cn/pc/index.html#/myAccount/a/6O2MaGg`. Read only visible page state. Do not inspect cookies, local storage, passwords, browser profiles, or session stores; do not call private page APIs or network endpoints; and do not use `computer-use` for this source.
2. The landing route above selects `汇总持仓`, not the required account. Click `华宝`, then require both the visible active-tab state and the resulting route `https://tzzb.10jqka.com.cn/pc/index.html#/myAccount/a/Ii8kkCY` before reading any amount. After every reload or navigation, confirm both signals again. Never read account amounts from `汇总持仓`, `我的账户`, `爱基金`, or `平安`, even when one of those tabs is the landing view or shows numeric values.
3. Determine the latest completed XSHG session. Accept the web holding only when its displayed update/valuation date reaches that session. On Monday before the XSHG close, the required date is the previous XSHG trading day, normally Friday.
4. Extract only explicitly displayed values from `华宝`: valuation/update date, total assets, the five strategy-asset amounts, cash, non-strategy positions within that account, instrument names, and recognition notes. Treat an absent strategy asset as zero only when the complete unfiltered holding list is visibly present, every displayed row has been extracted, and the recognition note records that the asset was absent from that complete list. Otherwise ask instead of inferring. Do not derive a missing total or cash balance from a rounded position ratio, and do not supplement the snapshot with values from another tab.
5. Apply the Account Consistency Gate below. Treat a gate failure as unavailable account data, not as a real zero balance.
6. When the page is accessible but its data is missing, stale, inconsistent, or not synchronized, lead with `需要你操作：访问投资账本app，等待账户数据更新后告诉我继续。` After the user says the update is complete, reload the original URL, select `华宝`, and retry.
7. When the page requires authentication or the session expired, lead with `需要你操作：请在当前 Chrome 中登录投资账本账号，完成后告诉我继续。` Never ask for, read, or enter the user's credentials. After the user says login is complete, reload the original URL, select `华宝`, and retry.
8. Request a holding screenshot when the host's authenticated Chrome adapter is unavailable, the visible DOM remains incomplete or unreadable, or the Investment Ledger page still fails after the applicable manual update or login step and retry. Do not insert `computer-use` between these two source levels. When a Hermes session lacks the required browser tools or cannot reach its configured CDP browser before navigation starts, lead with `当前 Hermes 会话缺少 Chrome 账户读取能力，因此无法开始读取投资账本。` Then ask the user to upload and confirm a complete `华宝` holding screenshot. Use `需要你操作：投资账本读取仍失败，请上传并确认最新持仓截图。` only after page access actually started and then failed.

### Account Consistency Gate

Stop before confirmation or `rebalance` when any condition holds:

- `华宝` is not visibly selected, the route is not `/pc/index.html#/myAccount/a/Ii8kkCY`, or any value came from `汇总持仓`, `我的账户`, `爱基金`, or `平安`.
- Any holding amount is positive while displayed total assets are zero or negative.
- The sum of explicitly displayed holdings, cash, and non-strategy amounts exceeds total assets beyond CNY 0.02.
- The valuation/update date is older than the latest completed XSHG session.
- Dates or totals come from different tabs, routes, or refresh states.
- Total assets or cash are absent and would need to be inferred from a rounded allocation percentage.
- A missing asset would be treated as zero even though the holding list is filtered, incomplete, or not fully extracted.

Use `ACCOUNT_SUMMARY_INCONSISTENT` as the reason when nonzero holdings coexist with a zero account total. Do not save zero as the actual total.

Do not silently replace a failed web read with the last record in `portfolio_data/records.jsonl`. That record may be identified as prior context, but it is not a fresh holding source. Reuse it for an account plan only when the user explicitly asks to use that dated snapshot and confirms that no trades, cash flows, or other account changes occurred after it.

Both Chrome-DOM-read holdings and screenshot-recognized holdings must pass the same explicit confirmation gate before `rebalance` appends a record. The account source may change the account amount plan only; it must never change the strategy signal, model state, or run manifest.

## User Action First

Keep `strategy_action`, `account_action`, plan `status`, identities, and reason codes unchanged in JSON and audit artifacts. The user-facing response exists to answer one question first: **What does the user need to do now?**

Lead with exactly one concise primary action, chosen in this order:

1. Authority or freshness validation failed → `暂停操作：当前信号未通过验证。`
2. Cache confirmation is required → `需要你确认：是否使用截至 [date] 的本地缓存？`
3. Newly read Chrome-DOM holdings or a fallback screenshot are not confirmed → `需要你确认：以下持仓信息是否准确？`
4. Investment Ledger needs a manual sync → `需要你操作：访问投资账本app，等待账户数据更新后告诉我继续。`
5. Investment Ledger needs authentication → `需要你操作：请在当前 Chrome 中登录投资账本账号，完成后告诉我继续。`
6. Hermes lacks the required browser runtime before page access starts → `当前 Hermes 会话缺少 Chrome 账户读取能力，因此无法开始读取投资账本。` Then request a complete `华宝` holding screenshot.
7. Investment Ledger access started but still fails after the applicable retry → `需要你操作：投资账本读取仍失败，请上传并确认最新持仓截图。`
8. A verified plan has `account_action=TRADE` and `status=pending` → `需要你操作：按下表调仓（尚未执行）。`
9. A verified plan has `account_action=HOLD` and `status=satisfied` → `当前无需操作。`

After the primary action, use at most one short reason sentence and only the information needed to complete or verify that action:

- For rebalancing, show the five ETF orders with current amount, target amount, and buy/sell amount, then show cash and non-strategy residuals separately.
- For a holding update or confirmation, show only the required source fields or the confirmation table.
- Give data end, holding valuation date, and holding source in one compact context line.
- Show blocking errors and material staleness warnings; omit routine validator details after they pass.

Do not routinely display `目标仓位是否更新`, raw `HOLD` / `TRADE` / `pending` values, pending identity, run ID, or internal reason codes. Provide them only when the user asks for technical details. If `supersedes_plan_id` is present, add `已替代上一计划` as a short note.

## Signal Mode

1. Locate the investment project root and read the nearest `AGENTS.md`.
2. Pass `NautilusTrader Authority Gate`, then run:

```bash
"<project-root>/.venv/bin/python" "<project-root>/scripts/portfolio_workbench_tool.py" --project-root "<project-root>" signal
```

3. Before strategy computation, refresh all five production caches and require their common data end to equal `latest_completed_xshg_session`. At Monday 09:00 Beijing time this is the previous XSHG trading day, normally Friday. The rev12 freshness gate is authoritative; an unfinished current session, missing common close, excessive forward-fill staleness, or mixed cache generation is blocking.
4. Present `market_refresh.message` first when refresh fails. In an unattended scheduled run, stop without `--no-refresh`, do not publish a conclusion from cache, and report the missing required session. In an interactive run only, a usable cache may be retried with `--no-refresh` after explicit user confirmation.
5. After the authority validator passes, present only data end, strategy action and reason, exact five-asset target weights, execution date when available, and actionable warnings.

`signal` writes only the account-independent decision to `portfolio_data/outputs/latest_signal.json`. It must not read `portfolio_data/records.jsonl`, open Investment Ledger, call the account adapter, or create a new account plan. Any prior `latest_execution_plan.json` is archived under `superseded_execution_plans/` when the new signal is published. Actual holdings must never feed back into the strategy signal.

## Account Mode

1. Require an existing `latest_signal.json` whose authority validation passes and whose data end equals the latest completed XSHG session. If it is missing or stale, complete Signal Mode first; do not regenerate the strategy inside `rebalance`.
2. Apply `Account Holding Source` and its consistency gate. Continue directly to a screenshot only after the authenticated Chrome adapter fallback condition is met.
3. Extract valuation date, total assets, the five strategy-asset amounts, cash, non-strategy positions, ETF names, and recognition notes from the selected source. Ask when a material field is unreadable; do not infer missing amounts from rounded percentages.
4. Confirm the actual Nasdaq/QDII instrument before assigning overseas equity. Do not map an S&P 500 fund to Nasdaq without explicit approval.
5. Default mappings:
   - `成长ETF易方达` → `cni_growth`
   - `价值ETF易方达` → `cni_value`
   - confirmed Nasdaq/QDII fund → `nasdaq`
   - `易方达新综债LOF` → `china_bond_composite`
   - `黄金9999` or confirmed domestic gold ETF → `gold`
6. Lead with `需要你确认：以下持仓信息是否准确？`, then show one confirmation table with `资产类别`, `ETF名称`, `实际金额 CNY`, `当前权重 %`, `识别备注` and a compact source/update-date line.
7. Calculate weights from amounts divided by total assets. Never accept user-entered weights.
8. Save and generate amounts only after explicit confirmation. For an Investment Ledger read, omit `screenshot_path` and set `source_id` to `investment-ledger-web:Ii8kkCY:huabao`. For a fallback screenshot, include its absolute path and source name. Write the confirmed values to a UTF-8 JSON payload and run:

```bash
"<project-root>/.venv/bin/python" "<project-root>/scripts/portfolio_workbench_tool.py" --project-root "<project-root>" rebalance --payload "/tmp/holding-payload.json"
```

9. After saving, apply `User Action First`. If rebalancing is required, present each asset's current amount, target amount, buy/sell amount, and ETF name. Show cash and non-strategy residuals separately. If no trade is required, say `当前无需操作。` and stop.

`rebalance` consumes the verified `latest_signal.json`; it does not refresh market data or generate another strategy signal.

The confirmed flow appends `portfolio_data/records.jsonl` and writes `latest_execution_plan.json` without modifying `latest_signal.json`. It copies a file under `portfolio_data/uploads/screenshots/` only for the screenshot fallback; a confirmed Investment Ledger read is audited by `source_id` without creating a synthetic screenshot.

## Current Production Boundary

Strategy ID:

```text
equity_b0nqg_rb50_40_10_bond10_ewma20hl_b0c2afirstbreachz2h8_weekly_xshgcal_noinsurance_basegate5_etfpx_uncapped_exact
```

Production revision: `12`.

Production status: active NautilusTrader release.

Rev12 has no historical activation waiver. Every production signal must reach the latest completed XSHG session.

### 1. B0 and risk-budget base

- Fixed China bond target: 10%. Gold has no fixed allocation.
- B0 uses the 40-day growth-minus-value return spread and MA250/sample-SD250 Z score. The first weekly outward breach below −2σ selects growth; above +2σ selects value. Exit at zero or after eight weekly observations.
- B0, Nasdaq and gold share the 90% dynamic sleeve with target risk contributions 50%, 40% and 10%.
- Covariance: zero-mean EWMA over all jointly valid prior returns, with a 20-trading-day half-life and minimum 60-return warm-up. Before the first non-fallback weekly result, the model stays in cash.
- No single-asset cap.

### 2. Rebalance gate

- The 5% gate compares only aggregate B0, Nasdaq, bonds and gold on the XSHG weekly signal close.
- A B0 growth/value switch is executed independently of the aggregate gate while preserving current B0 total weight.
- Signals execute at the next XSHG session close.

### 3. Insurance

- Disabled. The artifact role name `protected` denotes a no-insurance mirror only.

### Execution

- Initialize once from 100% model cash, then preserve the continuous path.
- Decision at XSHG close + 2ns; frozen target executes no earlier than the next session close + 1ns.
- Long-only, 1x leverage, price precision 8 and size precision 12.
- Model NAV applies 0.0001 to buy notional and 0.0001 to sell notional.

## Data Contract

Mutable workbench data stays under `portfolio_data/`:

- `data_cache/*.csv`: five production-owned asset caches.
- `records.jsonl`: confirmed holding snapshots and their amount plans.
- `outputs/latest_signal.json`: latest account-independent shadow-strategy decision, including its normalized decision identity.
- `outputs/latest_execution_plan.json`: latest account action, referencing one strategy decision and one confirmed holding snapshot.
- `uploads/screenshots/`: copied confirmed screenshots from the fallback path only.

Nasdaq uses split-adjusted 513100 secondary-market closes; gold uses split-adjusted 518880 closes. Do not substitute USD index or spot-gold series.

Historical `config_events.jsonl` may remain on disk as inert audit data. It is not read by the current workbench and there is no command for changing strategy parameters.

## Safety And Boundaries

- Keep one explicit confirmation gate for both Investment Ledger reads and fallback screenshots.
- Keep the account-source fallback exactly two levels: authenticated Chrome DOM control first (`chrome:control-chrome` in Codex or Hermes native browser tools through the dedicated CDP profile), then a user-confirmed screenshot. Do not use `computer-use`.
- Do not invent unreadable amounts, dates, or ETF mappings.
- Do not present a stale prior amount plan as current.
- Warnings are advisory; validation failure stops generation.
- A missing, stale, mismatched, or non-Nautilus run manifest is a blocking validation failure.
- Do not show a net-worth curve.
- Do not expose retired menus, parameter editors, historical strategy variants, or inactive modules.

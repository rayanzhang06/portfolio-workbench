## MCP source precedence (2026-11-14)

All holdings acquisition uses the shared `scripts/collect_huabao_mcp.py` command first, invoked with project Python in both Codex and Hermes. See SKILL.md for the tested MCP identity, current-data date convention and confirmation contract. Only after MCP failure may the host attempt its existing web reader once; older browser-first/reload instructions below apply only to that single fallback and do not authorize additional attempts. Model-only jobs remain account-independent. MCP monitor observations remain unconfirmed, expire after 24 hours and never enter account plans without explicit confirmation.

# Portfolio Workbench Data Contract

## User-Facing Operations

The workbench exposes only:

```text
signal
rebalance --payload <confirmed-holding-json>
```

Both operations require active production revision 12, NautilusTrader 1.230.0,
and an exact release binding to
`portfolio_workbench/nautilus_production_rev13/release_manifest.json`. The
complete `portfolio.nautilus_run.v1` and signal envelope must pass
`scripts/verify_nautilus_authority_v2.py` before publication or account
adaptation. Production rev4 is rollback-only and cannot generate a new signal.

`signal` and `rebalance` are deliberately separate. `signal` refreshes and
validates market data, publishes only `latest_signal.json`, and archives a
current account plan that no longer belongs to the newly published signal. It
does not read `records.jsonl` or call the account adapter. `rebalance` consumes
the already published and validator-passed `latest_signal.json`; it does not
refresh market data or generate another strategy run.

This separation is native to the frozen rev13 production workbench. Files under
`portfolio_workbench/nautilus_production_rev13/` and their release manifest stay
byte-for-byte immutable; all strategy computation originates from that
validated release.

The production account adapter is
`portfolio_workbench.nautilus_production_rev13.account_adapter:build_execution_plan`.
It consumes one verified signal path and one confirmed holding snapshot. It
cannot recalculate the strategy or modify the signal.

Before every signal run, the required data end is
`latest_completed_xshg_session`. At Monday 09:00 Beijing time this is the
previous XSHG trading day, normally Friday. All five caches must produce that
same common close. If refresh fails, a cache is reusable only when it reaches
that completed XSHG close. Otherwise `signal` returns
`status=market_data_unavailable` and publishes nothing. A valid fallback cache
still requires explicit confirmation before rerunning with `--no-refresh` in an
interactive session; scheduled runs fail closed and never use this fallback.

## Current Holding Resolution

- The primary source is the visible Investment Ledger account page at
  `https://tzzb.10jqka.com.cn/pc/index.html#/myAccount/a/Ii8kkCY`, read-only
  through authenticated Chrome DOM control. Codex uses the currently callable
  browser DOM adapter (`mcp__cua_repl.js` browser DOM/Playwright or structured
  page-text APIs), or legacy `chrome:control-chrome` when available. Read the
  selected adapter's documentation first. Hermes uses its built-in `browser_navigate`,
  `browser_snapshot`, `browser_click`, and `browser_console` tools attached by
  `browser.cdp_url` to a dedicated headed Hermes Chrome profile. Hermes must
  not depend on Codex's `node_repl` or `browser-client.mjs`. Read only visible
  DOM state; do not inspect browser secrets or call private page APIs or
  network endpoints. Browser DOM capability within `unified-computer-use` is
  allowed; native-app control, screenshot recognition and coordinate actions
  are not. A rejected browser permission must not be bypassed by changing adapters.
- Open the Huabao route directly. If redirected to the legacy summary route,
  click `华宝`, then require both its
  visible active state and the resulting route
  `https://tzzb.10jqka.com.cn/pc/index.html#/myAccount/a/Ii8kkCY`. Repeat both
  checks after every reload or route change. Never consume amounts from
  `汇总持仓`, `我的账户`, `爱基金`, or `平安`, even if one of those tabs is the
  landing view or shows numeric values.
- The web valuation/update date must reach the latest completed XSHG session.
  Nonzero holdings paired with a displayed zero total are inconsistent data,
  not a real zero balance. Reject the snapshot with
  `ACCOUNT_SUMMARY_INCONSISTENT`.
- Reject data when holdings, cash and non-strategy amounts exceed total assets
  by more than CNY 0.02, dates or totals cross tabs/refresh states, or total and
  cash would need to be inferred from a rounded allocation percentage.
- Treat an absent strategy asset as zero only when the full unfiltered holding
  list is visible and every displayed row was extracted. Record the absence in
  the recognition notes; otherwise ask rather than infer.
- If the page is stale or unsynchronized, ask the user to `访问投资账本app`, then
  reload and retry. If authentication is required, ask the user to log in in
  Chrome, then reload and retry; never request or enter credentials.
- Request a screenshot when the host's authenticated Chrome adapter is
  unavailable, the visible DOM is incomplete or unreadable, or the page still
  fails after the applicable user action and retry. The fallback is exactly
  Chrome DOM control then user-confirmed screenshot; do not insert screenshot
  or coordinate computer control. In Hermes,
  distinguish runtime unavailability before navigation (`当前 Hermes 会话缺少
  Chrome 账户读取能力，因此无法开始读取投资账本。`) from a page read that
  started and then failed (`投资账本读取仍失败`). Both sources require explicit
  user confirmation before `rebalance` saves them.
- Do not silently treat the last record in `records.jsonl` as current after a
  failed web read. Reuse it only after the user explicitly selects that dated
  snapshot and confirms that no account changes occurred after it.
- A plan is current only when its decision run and pending identity match the
  latest verified signal. A new signal never rebuilds an account plan from
  history; it archives any prior latest plan as superseded.

## Display-only Monitor Observation

For an authorized display-only monitor refresh, macOS native Chrome
accessibility text is also permitted, as specified in SKILL.md. This path does
not attach a browser debugger. It writes only an unconfirmed
`portfolio.monitor_observation.v1` with `capture_method=macos-accessibility-chrome`;
it cannot confirm holdings or create account plans. A native screenshot may
verify active-tab appearance, but amounts and dates come from accessibility text.
The exact Huabao route, complete list, current valuation date and reconciliation
checks still apply. Source-upload and observation times remain separate fields.

The 2026-09-19 approved GitHub Pages monitor is public. Account read failure does
not block model refresh: only a freshly refreshed, authority-verified model can
be newly published, with absent accounts or explicitly stale last-published
observations retaining their original dates. Stale observations have null model
amounts, model weights and deviations; no trade plans are published. Do not read
confirmed account records as an automatic fallback. Publication journals retain
validated model artifacts and file hashes for resumable deployment. Display SLA
(next morning 08:30) does not relax production freshness. Native standalone AX
collection is a prototype; retain the heartbeat trigger until full acceptance.

## Active Production Rev13 Strategy

```text
equity_b0nqcg_rb45_45_2_8_cba21801_ewma20hl_t1_b0c2afirstbreachz2h8_weekly_xshgcal_noinsurance_basegate5_uncapped_exact
```

- Production revision: `13`.
- The joint risk budget assigns B0, Nasdaq, CBA21801 and gold target risk
  contributions 45%, 45%, 2% and 8%.
- Covariance is zero-mean EWMA over all jointly valid returns through the preceding XSHG session, using a
  20-trading-day half-life and a 60-return warm-up. Before the first valid
  weekly risk-budget result, the model stays in cash.
- B0 uses weekly first outward breach at 2 sigma and exits at zero or after
  eight weekly observations.
- The 5% gate applies only to aggregate B0/Nasdaq/bond/gold weights. A B0 style
  switch preserves aggregate B0 weight and is not blocked by this gate.
- Insurance is disabled.
- Signals are decided at the calendar-known XSHG weekly close and execute at the
  next XSHG session close. Buys and sells each pay 0.0001; no slippage.

## Market Data

- `cni_growth`: CNI 980080.
- `cni_value`: CNI 980081.
- `nasdaq`: split-adjusted 513100 secondary-market close.
- `china_bond_composite`: CBA21801 ChinaBond 30-year Treasury wealth index. Confirmed account instrument is 511090. The prior 161119 position is classified separately as non-strategy.
- `gold`: split-adjusted 518880 secondary-market close.

The common mainland session calendar is authoritative. ETF observations may be
forward-filled for at most two common sessions. An unfinished current session,
missing latest completed session, excessive staleness, or calendar conflict is
a hard failure. Rev13 has no historical activation exception.

## Mutable Files

`portfolio_data/` is the only mutable root:

- `data_cache/{cni_growth,cni_value,nasdaq,china_bond_composite,gold}.csv`
- `records.jsonl`
- `outputs/latest_signal.json`
- `outputs/latest_execution_plan.json`
- `outputs/nautilus_runs/`
- `outputs/superseded_execution_plans/`
- `uploads/screenshots/` (screenshot fallback only)

## Signal And Plan Contracts

The production signal schema is `portfolio_workbench.daily_signal.v5`. It
contains strategy/revision, active status, framework, data end, strategy action,
reason, exact target, pending identity, linked reference/protected run IDs,
manifest path and manifest, normalized decision, and input/prior/next state
identities. It contains no actual-account input.

The account plan schema is
`portfolio_workbench.nautilus_execution_plan.v1`. It binds one decision and one
confirmed snapshot, keeps `strategy_action` separate from `account_action`, and
lists five concrete CNY orders. The plan identity includes a digest of snapshot
date, total value, amounts and ETF mappings.

## Confirmed Holding Payload

```json
{
  "valuation_date": "YYYY-MM-DD",
  "total_value": 100000.0,
  "asset_amounts": {
    "cni_growth": 0.0,
    "cni_value": 0.0,
    "nasdaq": 0.0,
    "china_bond_composite": 0.0,
    "gold": 0.0
  },
  "cash_amount": 0.0,
  "non_strategy_amount": 0.0,
  "etf_names": {},
  "screenshot_path": null,
  "source_id": "investment-ledger-web:Ii8kkCY:huabao",
  "confirmed": true
}
```

For a confirmed Investment Ledger read, omit `screenshot_path` or set it to
`null`. For a screenshot fallback, provide its absolute path and use its file
name as `source_id`. Weights are always derived from amounts. The seven amounts
must reconcile to `total_value` within CNY 0.02.

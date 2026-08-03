# Portfolio Workbench Data Contract

## User-Facing Operations

The workbench exposes only:

```text
signal
rebalance --payload <confirmed-holding-json>
```

`signal` produces the account-independent daily shadow-strategy decision. `rebalance` saves a confirmed screenshot holding and returns a separate account action with concrete CNY target and trade amounts.

Both operations are blocked unless the active production channel is NautilusTrader and the referenced `portfolio.nautilus_run.v1` passes `scripts/verify_nautilus_authority.py`. The current production rev4 is frozen during migration; staged rev5 must not be treated as active before explicit approval.

The staged rev5 account adapter is `portfolio_workbench.nautilus_account_adapter:build_execution_plan`. It consumes a validator-passed signal path and one confirmed holding snapshot, never recalculates the strategy, never modifies the signal, and marks a prior amount plan superseded whenever the decision or snapshot identity changes. It becomes user-facing only after explicit promotion.

If refresh fails while local cache is usable, either command returns `status=cache_confirmation_required` without writing a signal, plan, screenshot, or record. After user confirmation, rerun with `--no-refresh`.

## Default Holding Resolution

- A screenshot attached in the current request takes precedence and must pass the recognition and confirmation gate before `rebalance` saves it.
- Without a new attachment, use the last valid appended confirmed holding in `records.jsonl` and its saved screenshot as the default actual-account snapshot. Append order, rather than filesystem modification time, defines “most recent”.
- Reusing that snapshot calls `signal`; it does not copy the screenshot again or append another record. When the holding exists, `signal` regenerates `latest_execution_plan.json` against the new decision.
- The regenerated plan is current only when its `decision_ref.decision_id` equals the new signal's `decision_id`. Present the reused screenshot source and valuation date alongside the account action.
- Ask for a new screenshot only when no valid confirmed upload is available.

## Market Refresh

- `cni_growth` and `cni_value` come from the official CNI HTTPS history endpoint for index codes `980080` and `980081`. The response code and index name must match before the cache is accepted; transient connection and server failures are retried.
- Nasdaq, China Bond Composite, gold, and USD/CNY continue to use their declared AKShare sources.
- A refresh is all-or-nothing: all six cache files must download successfully before any live cache file is replaced.

## Current Strategy

```text
equity_rb25_25_50_bond15_gold10_lw504_p90any_refnav_dd15lock_c2_bond90gold10_threshold5
```

Production revision: `4` (frozen; no new authoritative signal generation).

Staged candidate: revision `5`, same strategy ID, `nautilus_trader==1.230.0`, `exchange_calendars==4.13.2`, `BacktestNode + ParquetDataCatalog`. Promotion remains a separate approval.

The canonical skill and `portfolio_workbench` package are production. `portfolio-dev` is a candidate/test channel whose revision may be equal to or greater than production; its output is not executable production guidance until explicitly promoted.

- Equity risk-budget sleeve: 75% of capital.
- Equity risk-contribution targets: `cni_growth=0.25`, `cni_value=0.25`, `nasdaq=0.50`.
- Fixed base: bonds 0.15, gold 0.10.
- Covariance: Ledoit-Wolf, 504 observations strictly before the monthly check date.
- P90: either 21d or 63d window cuts 50%; both cut 100%; only equities participate; released weight goes to bonds with an 0.80 cap.
- Insurance: an uninsured reference NAV independently runs the normal strategy; its rolling-504 peak is frozen on first F entry and retained through exits/re-entries until reference-NAV recovery; −15% entry / −15% recovery; two-close confirmation; defense is bonds 0.90, gold 0.10, equities 0.00.
- Ordinary gate: maximum absolute deviation at least 0.05.
- The shadow portfolio builds once at the first valid replay event; ordinary checks are monthly and insurance state changes bypass the ordinary gate.
- Execution rounding: 0.01.
- Model transaction cost: 0.0001 on buy notional and 0.0001 on sell notional.

## Mutable Files

`portfolio_data/` is the only mutable root:

- `data_cache/{cni_growth,cni_value,nasdaq,china_bond_composite,gold,usdcny}.csv`
- `records.jsonl`
- `outputs/latest_signal.json`
- `outputs/latest_execution_plan.json`
- `uploads/screenshots/`

`config_events.jsonl` is ignored legacy audit data and is not a recommendation input.

## Signal Contract

Schema: `portfolio_workbench.daily_signal.v3`.

The root exposes strategy/schema IDs, generation/data/check dates, `strategy_action`, strategy reason, execution step, equity risk-budget specification, P90 contract, insurance state, warnings, five shadow actions, and the normalized decision. It contains no actual-account holding input.

Each action exposes shadow pre-trade weight, base weight, equity risk contribution where applicable, P90 measurements and cuts, normal target, insurance-effective exact target, rounded model target, shadow post-trade weight, strategy trade weight, and direction.

The active Nautilus signal must also expose `run_id`, `reference_run_id`, `run_manifest_path`, and an embedded `portfolio.nautilus_run.v1`. The manifest binds the release, framework version, input snapshot, XSHG calendar, catalog/config, initial state, reference dependency, and event/fill/position/result digests. Actual-account inputs are excluded.

## Rebalance Plan Contract

Schema: `portfolio_workbench.rebalance_plan.v3`.

The root exposes strategy/schema IDs, decision and holding-snapshot references, separate `strategy_action` and `account_action`, holding/data/check dates, trigger, insurance, total account value, five orders, cash/non-strategy residuals, and trade totals. A screenshot confirms holdings; it is not execution acknowledgement.

Each order exposes asset key/name, confirmed ETF name, current amount and weight, target amount and weight, signed trade amount, and buy/sell/hold direction.

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
  "screenshot_path": "/absolute/path/to/image",
  "source_id": "image-name",
  "confirmed": true
}
```

Weights are always derived from amounts. The seven amounts must reconcile to `total_value` within CNY 0.02.

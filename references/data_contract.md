# Portfolio Workbench Data Contract

## User-Facing Operations

The workbench exposes only:

```text
signal
rebalance --payload <confirmed-holding-json>
```

`signal` produces the holdings-aware daily model signal. `rebalance` saves a confirmed screenshot holding and returns concrete CNY target and trade amounts.

If refresh fails while local cache is usable, either command returns `status=cache_confirmation_required` without writing a signal, plan, screenshot, or record. After user confirmation, rerun with `--no-refresh`.

## Market Refresh

- `cni_growth` and `cni_value` come from the official CNI HTTPS history endpoint for index codes `980080` and `980081`. The response code and index name must match before the cache is accepted; transient connection and server failures are retried.
- Nasdaq, China Bond Composite, gold, and USD/CNY continue to use their declared AKShare sources.
- A refresh is all-or-nothing: all six cache files must download successfully before any live cache file is replaced.

## Current Strategy

```text
equity_rb25_25_50_bond15_gold10_lw504_p90any_dd10r504_c2_threshold5
```

Production revision: `1`.

The canonical skill and `portfolio_workbench` package are production. `portfolio-dev` is a candidate/test channel whose revision may be equal to or greater than production; its output is not executable production guidance until explicitly promoted.

- Equity risk-budget sleeve: 75% of capital.
- Equity risk-contribution targets: `cni_growth=0.25`, `cni_value=0.25`, `nasdaq=0.50`.
- Fixed base: bonds 0.15, gold 0.10.
- Covariance: Ledoit-Wolf, 504 observations strictly before the monthly check date.
- P90: either 21d or 63d window cuts 50%; both cut 100%; only equities participate; released weight goes to bonds with an 0.80 cap.
- Insurance: strategy self-NAV rolling-504 drawdown; −10% entry / −10% recovery; two-close confirmation; defense is bonds 0.80, gold 0.10, equities 0.10.
- Ordinary gate: maximum absolute deviation at least 0.05.
- Build month and insurance state change force execution.
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

Schema: `portfolio_workbench.daily_signal.v1`.

The root exposes strategy/schema IDs, generation/data/check dates, holding date, mode, `trade_required`, trigger diagnostics, execution step, equity risk-budget specification, P90 contract, insurance state, warnings, five actions, and cash/non-strategy residuals.

Each action exposes current weight, base weight, equity risk contribution where applicable, P90 measurements and cuts, normal target, insurance-effective exact target, execution target, trade weight, and direction.

## Rebalance Plan Contract

Schema: `portfolio_workbench.rebalance_plan.v1`.

The root exposes strategy/schema IDs, holding/data/check dates, trigger, insurance, total account value, five orders, cash/non-strategy residuals, and trade totals.

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

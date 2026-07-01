---
name: portfolio-workbench
description: Use this skill when the user wants to run the portfolio rebalance workbench inside Codex instead of the web UI, including strategy summaries, ERC target weights, risk warnings, holding screenshot confirmation, rebalance guidance, JSON/JSONL records, and record history.
---

# Portfolio Workbench

## Overview

This skill turns the rebalance workbench into a Codex-native interaction. It keeps the prior product logic, but replaces the browser form with a conversational menu, screenshot confirmation, and plain JSON/JSONL storage under `portfolio_data/`.

Always use the project package `portfolio_workbench` as the execution source. Do not reimplement allocation math in the prompt, do not use the old web UI, and do not import or read runtime files from `portfolio-dev/`.

## Startup Flow

1. Locate the investment project root. In this workspace it is normally the current working directory.
2. Read the nearest `AGENTS.md` before editing or running project code.
3. Run the summary through the project-local wrapper at `<project-root>/scripts/portfolio_workbench_tool.py`. If that file is missing in an older checkout, use the skill-local fallback at `<this-skill-dir>/scripts/portfolio_workbench_tool.py`. Always pass `--project-root <project-root>` explicitly; do not assume `scripts/portfolio_workbench_tool.py` is relative to the current shell directory.
4. Present, in this order:
   - latest holding record;
   - latest recommended allocation;
   - risk warning;
   - current strategy module parameters: ERC base, reward-risk active tilt, and risk-control status;
   - market status, including market refresh status, check date, and data end date;
   - native option tabs for all operation choices.
5. If market refresh fails but local cache exists, tell the user the exact failure and ask whether to continue using local cache or abort the session before showing operation choices. Use `request_user_input` when available with choices `继续使用本地缓存 (Recommended)` and `中止本轮`; only render the operation menu after the user chooses to continue. If there is no usable local cache, stop and explain the blocker.

Use Codex's native `request_user_input` control for the menu whenever the tool is available. Do not render the menu only as plain text bullets. The summary payload includes `startup_report_sections` and `menu_tabs`; first render the overview strictly in the order declared by `startup_report_sections`, handle any market-refresh fallback decision, then render the native option cards from `menu_tabs`.

Render the operation choices as a two-layer structure:

- `组合操作`
- `信息查询`

Then show the second layer for the chosen tab:

- `组合操作`: `持仓截图上传 & 调仓建议生成 (Recommended)`, `查看策略模块参数`, `查看主动偏离状态`
- `信息查询`: `查看配置历史与数据状态`, `查看历史持仓记录`, `查看最新执行计划`

If `request_user_input` is available, use one native question for the top-level tab and one native question for the second-level options under the chosen tab. If `request_user_input` is not available in the current runtime, show the same two-layer structure in plain text and ask the user to reply with an option label.

## Data Rules

All mutable skill data is stored under `portfolio_data/`:

- `data_cache/*.csv`: copied market cache used by this skill.
- `records.jsonl`: append-only holding records and execution snapshots.
- `config_events.jsonl`: append-only historical baseline configuration events.
- `outputs/latest_execution_plan.json`: latest actionable execution plan.
- `uploads/screenshots/`: copied holding screenshots.

The skill only reads and writes under `portfolio_data/` at runtime. It must not reference `portfolio-dev/` or any removed local web workbench files. Network refresh writes to a temporary directory and then copies validated CSVs into `portfolio_data/data_cache/`.

## Holding Screenshot Flow

When the user chooses 实盘记录 / 上传持仓截图:

1. Ask the user to upload the latest holding screenshot if it is not already attached.
2. Use model vision to extract:
   - valuation date if visible, otherwise ask;
   - total assets;
   - strategy asset market values;
   - cash / available amount;
   - non-strategy positions, if any;
   - ETF names and recognition notes.
3. Map ETF names to strategy asset classes:
   - `标普500ETF华夏` -> `纳斯达克` as overseas equity proxy.
   - `价值ETF易方达` -> `A股价值`.
   - `易方达新综债LOF` -> `中证全债`.
   - `黄金ETF华夏` -> `黄金`.
   - Missing `A股成长` is allowed and should be confirmed as zero.
4. Show one confirmation table with columns: `资产类别`, `ETF名称`, `实际金额 CNY`, `当前权重 %`, `识别备注`.
5. Do not let the user edit weights directly. Weights are always calculated from amounts divided by total assets.
6. Ask the user to confirm or provide corrections. Save only after explicit confirmation.
7. Save by calling `<project-root>/scripts/portfolio_workbench_tool.py --project-root <project-root> save-record --payload <payload-json>`.

The saved record must include the copied screenshot path, holding amounts, computed weights, strategy config snapshot, market signal, and the generated execution plan.

## Strategy Logic

当前策略:

- The current strategy is `risk_asset_erc_reward_risk_tilt_bond20_dual_vol90_threshold5`.
- The recommendation pipeline must remain three independent modules:
  1. Base allocation: 中证全债固定为 20%；A股成长 / A股价值 / 纳斯达克 / 黄金 合计 80%，按过去 252 个共同交易日日收益协方差做 long-only 等风险贡献（ERC）分配。
  2. Active tilt: `reward_risk_tilt` with fidelity label `proxy_adaptation`; use shifted prices to avoid same-check-date look-ahead, calculate 252-trading-day reward/risk scores, and apply bounded active deviations to risk assets only.
  3. Risk control: apply dual-window 90th-percentile high-volatility cuts after active tilt.
- ERC 基准每月随最新行情缓存计算，不使用手动固定基准作为推荐配置来源。
- 主动偏离只允许来自程序化 `reward_risk_tilt` 模块，不再提供主观偏移、人工加减仓或 tactical offset 入口。
- Historical `subjective_offset` events may exist in old append-only logs, but they are audit-only records and must not be loaded into current strategy state, summaries, recommendations, or execution plans.

The legacy `save-baseline` command may remain available for audit compatibility, but it is not the current recommendation source. The legacy `save-offset` command is removed from the skill surface.

## Risk And Guidance Rules

The strategy logic is implemented by the project package:

- recommended allocation = risk-asset ERC base x reward-risk active tilt x dual-window high-volatility control x rebalance rule;
- active-tilt fields must be visible in summaries and execution plans: `active_tilt_id`, `active_tilt_fidelity_level`, `active_tilt_weight_before_risk`, `active_tilt_delta`, and `pre_risk_control_weight`;
- 63d high-volatility assets are cut by half;
- assets where both 21d and 63d high-volatility signals trigger are cut to zero;
- freed weight is redistributed by inverse 63d volatility to assets without a risk cut;
- rebalance guidance triggers when max deviation is at least 5%;
- execution targets are rounded to 1% steps;
- cash and non-strategy positions are shown in Chinese as `现金` and `非策略仓位`.

Do not show a net-worth curve. That feature has been removed from the skill surface.

## Commands

Preferred helper commands from the project root:

```bash
"<project-root>/.venv/bin/python" "<project-root>/scripts/portfolio_workbench_tool.py" --project-root "<project-root>" summary
"<project-root>/.venv/bin/python" "<project-root>/scripts/portfolio_workbench_tool.py" --project-root "<project-root>" history
"<project-root>/.venv/bin/python" "<project-root>/scripts/portfolio_workbench_tool.py" --project-root "<project-root>" latest-plan
"<project-root>/.venv/bin/python" "<project-root>/scripts/portfolio_workbench_tool.py" --project-root "<project-root>" save-record --payload "<payload-json>"
"<project-root>/.venv/bin/python" "<project-root>/scripts/portfolio_workbench_tool.py" --project-root "<project-root>" save-baseline --payload "<payload-json>"  # legacy audit command
```

Skill-local fallback for older project checkouts:

```bash
"<project-root>/.venv/bin/python" "<this-skill-dir>/scripts/portfolio_workbench_tool.py" --project-root "<project-root>" summary
```

Payload files should be UTF-8 JSON. Prefer temporary payload files under `/tmp` when constructing them during a Codex interaction.

The helper also auto-reexecs into `<project-root>/.venv/bin/python` when it is launched with another Python interpreter, so explicit `.venv` invocation is preferred but not mandatory.

Global options such as `--project-root` and `--data-root` are accepted before or after the subcommand for compatibility, but examples should keep them before the subcommand.

`latest-plan` should return exit 0 even before any execution plan exists. In that case it returns an `{"status":"empty", ...}` JSON payload so the Codex menu can render a graceful "暂无最新执行计划" state.

#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    project_root = _project_root_from_args(sys.argv[1:])
    if any(arg in {"signal", "rebalance"} for arg in sys.argv[1:]):
        _enforce_production_authority(project_root)
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from portfolio_workbench.cli import main as project_main

    project_main()


def _enforce_production_authority(project_root: Path) -> None:
    channels = json.loads((project_root / "strategy_channels.json").read_text())
    production = channels["production"]
    framework = production.get("framework") or {}
    if (
        production.get("status") != "active"
        or framework.get("name") != "NautilusTrader"
        or framework.get("version") != "1.230.0"
        or framework.get("runtime") != "BacktestNode+ParquetDataCatalog"
    ):
        print(
            json.dumps(
                {
                    "status": "production_frozen",
                    "message": (
                        "Production rev4 is frozen. Staged Nautilus rev5 requires "
                        "all gates and explicit promotion approval before signal/rebalance."
                    ),
                }
            )
        )
        raise SystemExit(2)


def _project_root_from_args(argv: list[str]) -> Path:
    for index, arg in enumerate(argv):
        if arg == "--project-root" and index + 1 < len(argv):
            return Path(argv[index + 1]).expanduser().resolve()
        if arg.startswith("--project-root="):
            return Path(arg.split("=", 1)[1]).expanduser().resolve()
    return Path.cwd().resolve()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    project_root = _project_root_from_args(sys.argv[1:])
    if any(
        command in sys.argv[1:]
        for command in ("staged-signal", "activation-signal")
    ):
        print(json.dumps({"status": "internal_command_not_available"}))
        raise SystemExit(2)
    if any(arg in {"signal", "rebalance"} for arg in sys.argv[1:]):
        _enforce_production_authority(project_root)
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from portfolio_workbench.nautilus_production_rev12.cli import main as project_main

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
        or production.get("revision") != 12
        or production.get("release_manifest")
        != "portfolio_workbench/nautilus_production_rev12/release_manifest.json"
    ):
        print(
            json.dumps(
                {
                    "status": "production_authority_failed",
                    "message": (
                        "Active production must be the exact frozen Nautilus rev12 "
                        "release before signal/rebalance."
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

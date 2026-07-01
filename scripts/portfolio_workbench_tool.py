#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    project_root = _project_root_from_args(sys.argv[1:])
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from portfolio_workbench.cli import main as project_main

    project_main()


def _project_root_from_args(argv: list[str]) -> Path:
    for index, arg in enumerate(argv):
        if arg == "--project-root" and index + 1 < len(argv):
            return Path(argv[index + 1]).expanduser().resolve()
        if arg.startswith("--project-root="):
            return Path(arg.split("=", 1)[1]).expanduser().resolve()
    return Path.cwd().resolve()


if __name__ == "__main__":
    main()

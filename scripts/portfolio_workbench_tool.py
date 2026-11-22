#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import sys


def project_root(args: list[str]) -> Path:
    for index, arg in enumerate(args):
        if arg == "--project-root" and index + 1 < len(args):
            return Path(args[index + 1]).expanduser().resolve()
        if arg.startswith("--project-root="):
            return Path(arg.split("=", 1)[1]).expanduser().resolve()
    return Path.cwd().resolve()


if __name__ == "__main__":
    command = project_root(sys.argv[1:]) / "scripts/portfolio_active_release.py"
    os.execv(sys.executable, [sys.executable, str(command), *sys.argv[1:]])

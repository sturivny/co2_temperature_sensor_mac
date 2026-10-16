#!/usr/bin/env python3
"""Create an isolated checkout-local tool environment; never configure hardware."""
from pathlib import Path
import subprocess
import sys
import venv

root = Path(__file__).resolve().parents[1]
if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10+ required")
environment = root / ".tooling/venv"
if not (environment / "bin/python").exists():
    venv.EnvBuilder(with_pip=True).create(environment)
subprocess.run([str(environment / "bin/python"), "-m", "pip", "install", "-r",
                str(root / "requirements-tools.txt")], check=True)
print("Ready. Build the Mac app with .tooling/venv/bin/python tools/build_macos.py")

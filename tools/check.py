#!/usr/bin/env python3
"""Offline software checks. Never access serial ports or change device settings."""
from pathlib import Path
import py_compile
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
for folder in ("tools", "enclosure/v0.8"):
    for source in (root / folder).glob("*.py"):
        py_compile.compile(str(source), doraise=True)
with tempfile.TemporaryDirectory(prefix="co2-check-") as folder:
    binary = Path(folder) / "journal_test"
    subprocess.run(["clang++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                    "-I" + str(root / "firmware/include"),
                    str(root / "tests/journal_test.cpp"), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
    if sys.platform == "darwin":
        subprocess.run([sys.executable, str(root / "tools/build_macos.py")], check=True)
        subprocess.run([str(root / "build/CO2 Monitor.app/Contents/MacOS/CO2Monitor"),
                        "--self-test", folder], check=True)
print("PASS: Python syntax and available host software checks")

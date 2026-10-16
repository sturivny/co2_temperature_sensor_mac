#!/bin/bash
cd -- "$(dirname -- "$0")" || exit 1
.tooling/venv/bin/python tools/board.py configure
read -r -p 'Нажмите Enter, чтобы закрыть окно…'

#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
mkdir -p .tools
if [ ! -d .tools/unrpyc/.git ]; then
  git clone https://github.com/CensoredUsername/unrpyc.git .tools/unrpyc
fi
git -C .tools/unrpyc checkout --detach 3ae8334ed71a05535927dcc559663d3aca51215b
.venv/bin/python .tools/unrpyc/unrpyc.py --version

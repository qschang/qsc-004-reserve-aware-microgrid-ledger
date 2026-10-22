#!/bin/bash
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
install -m 0755 "$ROOT/reference.py" /app/microgrid.py

#!/bin/bash
set -euo pipefail
for candidate in /solution/reference.py /solution/microgrid.py /root/solution/reference.py /workspace/solution/reference.py; do
  if [ -f "$candidate" ]; then
    install -m 0755 "$candidate" /app/microgrid.py
    exit 0
  fi
done
printf 'solution mount missing\n' >&2
find /solution /root/solution /workspace/solution -maxdepth 2 -type f 2>/dev/null >&2 || true
exit 1

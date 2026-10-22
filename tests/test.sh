#!/usr/bin/env bash
set -Eeuo pipefail
REWARD_PATH=/logs/verifier/reward.txt
REPORT_DIR=/logs/verifier
TMP="$REWARD_PATH.tmp.$$"
ok=0
mkdir -p "$REPORT_DIR"
printf '0.00\n' > "$REWARD_PATH"
cleanup_zero(){ if [ "$ok" -ne 1 ]; then printf '0.00\n' > "$REWARD_PATH"; fi; rm -f "$TMP"; }
trap cleanup_zero ERR INT TERM HUP EXIT
cd /tests
python3 -B -I -m pytest -q -p no:cacheprovider --junitxml="$REPORT_DIR/pytest.xml" /tests/test_microgrid.py >"$REPORT_DIR/pytest.log" 2>&1
printf '1.00\n' > "$TMP"
mv -f "$TMP" "$REWARD_PATH"
ok=1
trap - ERR TERM HUP INT


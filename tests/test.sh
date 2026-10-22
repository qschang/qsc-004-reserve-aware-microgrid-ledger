#!/usr/bin/env bash
set -Eeuo pipefail
REWARD_PATH=/logs/verifier/reward.txt
REPORT_DIR=/logs/verifier
TMP="$REWARD_PATH.tmp.$$"
mkdir -p "$REPORT_DIR"
printf '0.00\n' > "$REWARD_PATH"
cleanup(){ rc=$?; rm -f "$TMP"; if [ "$rc" -ne 0 ]; then printf '0.00\n' > "$REWARD_PATH"; fi; exit "$rc"; }
trap cleanup EXIT INT TERM HUP
cd /tests
python3 -B -I -m pip install --disable-pip-version-check --no-index --find-links=/tests/wheels --require-hashes -r /tests/requirements.txt >"$REPORT_DIR/install.log" 2>&1
python3 -B -I -m pytest -q -p no:cacheprovider --junitxml="$REPORT_DIR/pytest.xml" /tests/test_microgrid.py >"$REPORT_DIR/pytest.log" 2>&1
printf '1.00\n' > "$TMP"
mv -f "$TMP" "$REWARD_PATH"
trap - EXIT INT TERM HUP

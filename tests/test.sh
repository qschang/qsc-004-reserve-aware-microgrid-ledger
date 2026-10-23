#!/bin/bash
set -Eeuo pipefail
LOG_DIR=/logs/verifier
REWARD_FILE=/logs/verifier/reward.txt
STATUS_FILE="$LOG_DIR/verification-status.txt"
TEST_LOG="$LOG_DIR/test-stdout.txt"
completed=0
mkdir -p "$LOG_DIR"
write_reward(){ chmod 0644 "$REWARD_FILE" 2>/dev/null || true; printf '%s\n' "$1" > "$REWARD_FILE"; chmod 0444 "$REWARD_FILE"; }
write_status(){ chmod 0644 "$STATUS_FILE" 2>/dev/null || true; printf '%s\n' "$1" > "$STATUS_FILE"; chmod 0444 "$STATUS_FILE"; }
on_exit(){ if [ "$completed" -ne 1 ]; then write_status 'INCOMPLETE'; write_reward 0.000; fi; }
on_signal(){ write_status 'INCOMPLETE: interrupted'; write_reward 0.000; completed=1; exit 0; }
printf '0.000\n' > /logs/verifier/reward.txt; write_status 'INCOMPLETE'; trap on_exit EXIT; trap on_signal INT TERM HUP
python3 -m pip install --no-cache-dir --no-index --find-links=/tests/wheels pytest==8.4.2 >/tmp/pytest-install.log 2>&1 || { write_reward 0.000; completed=1; exit 0; }
RESULT_XML=$(mktemp "$LOG_DIR/pytest-results.XXXXXX"); rm -f "$RESULT_XML"
set +e
timeout 290s python3 -u -m pytest -v -s -p no:cacheprovider --junitxml="$RESULT_XML" /tests/test_outputs.py >"$TEST_LOG" 2>&1
rc=$?; set -e
if [ "$rc" -ne 0 ] && [ "$rc" -ne 1 ]; then write_reward 0.000; completed=1; exit 0; fi
if [ ! -s "$RESULT_XML" ]; then write_reward 0.000; completed=1; exit 0; fi
if ! python3 -c 'import sys, xml.etree.ElementTree as ET; root=ET.parse(sys.argv[1]).getroot(); assert len(root.findall(".//testcase")) > 0' "$RESULT_XML"; then write_reward 0.000; completed=1; exit 0; fi
if ! python3 /tests/score.py --config /tests/scoring.json --junit "$RESULT_XML" --report-out "$LOG_DIR/scoring-report.json" --reward-out "$REWARD_FILE"; then write_reward 0.000; completed=1; exit 0; fi
chmod 0444 "$REWARD_FILE"; write_status "COMPLETED: $(cat "$REWARD_FILE")"; completed=1; rm -f "$RESULT_XML"; exit 0


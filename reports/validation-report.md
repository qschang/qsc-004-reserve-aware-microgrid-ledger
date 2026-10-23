# Validation Report

## Target

Task: `qsc-004`, candidate package for a bounded renewable microgrid dispatch ledger. This report is preliminary until bound to a published commit and a clean POSIX snapshot.

## Results

- Environment build: not yet run for this candidate revision; Docker daemon preflight succeeded.
- Oracle: not yet run for this candidate revision.
- NOP: not yet run for this candidate revision.
- Domestic model: DeepSeek Chat trial is pending publication of this candidate; earlier trials belong to older commits and are not evidence for this candidate.
- Harbor CLI: version `0.24.0` is available at the project-local executable path.
- Docker daemon: `docker info` succeeded using the `desktop-linux` context.
- GitHub CLI: authenticated `gh` preflight succeeded for the configured account.
- Source network: GitHub access will be exercised through the required local HTTP proxy on port `7897` during publication.
- Blind red-team instruction-leakage review: pending on the clean published snapshot.

## Local Checks

- `MICROGRID_PATH=solution/reference.py python -m pytest -q`: 49 passed.
- `tests/scoring.json`: 29 weighted tests sum to `1.000`; 20 gate tests.
- `git diff --check`: passed before report additions.
- Full Harbor controls, Docker E2E, POSIX snapshot audit, mutation evidence, and the 64-rule audit remain pending for the published revision.

## Limits

These checks establish only local test behavior and tool availability. They do not establish domain-owner approval, model difficulty, mutation strength, runtime integrity, or release approval. Refresh this report after every candidate change and bind all final evidence to the same published Git commit and package digest.

# qsc-004 Validation Record

## Review Scope

The blind red-team review considered `instruction.md` and the agent-visible `environment/` tree before consulting tests or the reference solution. It found a local JSON interface, a renewable microgrid scenario, and no bundled business data. The task now describes dispatch accounting only; it does not claim a reserve product, network constraints, market settlement, or real telemetry.

The subsequent contract review mapped the commitment/ramp, storage, and power-balance challenges to the design card and named pytest cases. Hand calculations were made independently from the reference implementation. Rejection cases exercise both an absent destination and a pre-existing byte sentinel; the late-invalid case checks that no staged output is left behind. Atomic replacement failure is injected at `os.replace` after a valid baseline publication.

## Comparison and Provenance

The user-provided YEL examples were used as process comparators for compact operational objectives, local reproducibility, explicit test matrices, and hand-checkable correctness evidence. Their reported approval status was not treated as evidence for this package. The EN-07 and EN-04 research packs were inspected; both label their contents as candidate material. Their source indexes are recorded as leads, not as expert certification. Synthetic fixtures are hand-authored and do not represent measured operations.

## Executed Checks

- Local reference validation: 23 pytest cases passed after the latest test edits.
- Test-quality static check: source analysis found direct assertions in behavior-test bodies; a UTF-8 console rerun is still required because the default Windows GBK stream rejected a warning glyph.
- Environment build status: pending the final pushed revision.
- Harbor CLI status: installed at `di/work/harbor-venv/Scripts/harbor.exe`, version 0.24.0.
- Docker daemon status: available through the `desktop-linux` context.
- GitHub CLI status: authenticated as `qschang`; repository push credentials are available.
- Source network status: available; task execution has no external service dependency.
- Harbor Oracle/NOP and DeepSeek Chat trials: pending the final pushed revision. No score or model-difficulty claim is made here.
- Domestic model status: not required by the current user request; no domestic model result is claimed.
- Mutation replay, clean POSIX snapshot audit, and final 64-rule audit: pending the same frozen revision.

## Limitations

This record is an implementation review, not a human domain-editorial attestation or a release approval. No human sign-off is claimed. The package remains a candidate until all revision-bound runtime, mutation, model, and final audit evidence is complete and independently inspectable.

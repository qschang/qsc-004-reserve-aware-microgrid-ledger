# Reference solution coverage

The reference implementation is intentionally independent of the verifier and covers three domain challenges:

1. `UNIT-01`: commitment-duration state and initial/inter-hour ramp feasibility. Tests: `CASE-QSC004-MIN-UP`, `CASE-QSC004-MIN-DOWN`, and `CASE-QSC004-RAMP-INITIAL`.
2. `STOR-02`: efficiency-aware storage recursion, charging surplus before curtailment, and using available storage before unserved load. Tests: `CASE-QSC004-SOC-RECURRENCE`, `CASE-QSC004-SURPLUS-CHARGE`, `CASE-QSC004-STORAGE-LAST-RESORT`, and `CASE-QSC004-SOC-CAPACITY`.
3. `BAL-03`: renewable-first supply, unserved-energy penalty, startup accounting, and per-period conservation. Tests: `CASE-QSC004-RENEWABLE`, `CASE-QSC004-UNSERVED`, `CASE-QSC004-BALANCE`, and `CASE-QSC004-STARTUP-COST`.

The expected values are checked from the public equations and hand calculations, not copied from verifier output. Deterministic ordering, exact output shape, commitment accounting, and atomic rejection are additional contract-integrity checks rather than separate domain-difficulty axes.

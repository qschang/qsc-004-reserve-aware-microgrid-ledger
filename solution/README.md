# Reference solution coverage

The reference implementation is intentionally independent of the verifier and covers three domain challenges:

1. `UNIT-01`: commitment-duration state, initial/inter-hour ramp feasibility, and the distinction between a must-run commitment and its minimum feasible power before merit-order increments. Tests: `CASE-QSC004-MIN-UP`, `CASE-QSC004-MIN-DOWN`, `CASE-QSC004-RAMP-INITIAL`, and `CASE-QSC004-MUST-RUN-BALANCE`.
2. `STOR-02`: efficiency-aware storage recursion, charging surplus before curtailment, and using available storage before unserved load. Tests: `CASE-QSC004-SOC-RECURRENCE`, `CASE-QSC004-SURPLUS-CHARGE`, `CASE-QSC004-STORAGE-LAST-RESORT`, and `CASE-QSC004-SOC-CAPACITY`.
3. `BAL-03`: renewable-first supply, unserved-energy penalty, startup accounting, deterministic merit-order ties, and per-period conservation. Tests: `CASE-QSC004-RENEWABLE`, `CASE-QSC004-UNSERVED`, `CASE-QSC004-COST-LEDGER`, `CASE-QSC004-BALANCE`, `CASE-QSC004-STARTUP-COST`, `CASE-QSC004-STARTUP-NOT-OBJECTIVE`, and `CASE-QSC004-TIE-ORDER`.

Initial minimum-down expiry is covered by `CASE-QSC004-INITIAL-DOWN-EXPIRY`; this is a transition-boundary cross-check for `UNIT-01`.

4. `RES-04`: N-1 spinning-reserve accounting across online-unit outages, the no-online-unit case, and deliverable storage energy. Reserve is a validation constraint over the fixed dispatch policy. Tests: `CASE-QSC004-N1-RESERVE`, `CASE-QSC004-RESERVE-STORAGE-ONLY`, `CASE-QSC004-RESERVE-STORAGE-ENERGY`, and `CASE-QSC004-RESERVE-SHORTFALL`.
5. `JSON-05`: exact object schemas, duplicate-member rejection, and the distinction between JSON booleans and integers. Tests: `CASE-QSC004-REJECT-DUPLICATE-MEMBER`, `CASE-QSC004-REJECT-BOOLEAN-HORIZON`, and `CASE-QSC004-REJECT-BOOLEAN-DURATION`.

The expected values are checked from the public equations and hand calculations, not copied from verifier output. Deterministic ordering, exact output shape, commitment accounting, and atomic rejection are additional contract-integrity checks rather than separate domain-difficulty axes.

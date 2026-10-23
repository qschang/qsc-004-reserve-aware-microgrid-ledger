# Reference solution coverage

The reference implementation is intentionally separate from the test runner and covers three independent domain challenges:

1. `UNIT-01`: feasible commitment-state transitions, ramp and minimum-output constraints, and globally optimal startup decisions across the horizon. Tests: `CASE-QSC004-MIN-UP`, `CASE-QSC004-MIN-DOWN`, `CASE-QSC004-INITIAL-DOWN-EXPIRY`, `CASE-QSC004-DOWN-LOCKOUT`, `CASE-QSC004-RAMP-INITIAL`, `CASE-QSC004-RAMP-DOWN-STORAGE`, `CASE-QSC004-MUST-RUN-BALANCE`, `CASE-QSC004-MINIMUM-OUTPUT-FEASIBILITY`, `CASE-QSC004-START-MINIMUM-EXCEEDS-DEFICIT`, `CASE-QSC004-START-RAMP-FEASIBILITY`, `CASE-QSC004-STARTUP-OBJECTIVE`, `CASE-QSC004-GLOBAL-STARTUP-PLAN`, `CASE-QSC004-OPTIMAL-UNSERVED`, and `CASE-QSC004-OPTIMAL-RESERVE-COMMITMENT`.
2. `STOR-02`: efficiency-aware storage recursion, charging surplus before curtailment, and using available storage before unserved load. Tests: `CASE-QSC004-SOC-RECURRENCE`, `CASE-QSC004-SURPLUS-CHARGE`, `CASE-QSC004-STORAGE-LAST-RESORT`, and `CASE-QSC004-SOC-CAPACITY`.
3. `RES-04`: N-1 reserve accounting across online-unit outages, storage-only reserve, deliverable storage energy, and reserve feasibility as part of the commitment decision. Tests: `CASE-QSC004-N1-RESERVE`, `CASE-QSC004-RESERVE-STORAGE-ONLY`, `CASE-QSC004-RESERVE-STORAGE-ENERGY`, `CASE-QSC004-RESERVE-SHORTFALL`, and `CASE-QSC004-OPTIMAL-RESERVE-COMMITMENT`.

Initial minimum-down expiry is covered by `CASE-QSC004-INITIAL-DOWN-EXPIRY`; this is a transition-boundary cross-check for `UNIT-01`.

4. `RES-04`: N-1 spinning-reserve accounting across online-unit outages, the no-online-unit case, and deliverable storage energy. Reserve is a validation constraint over the fixed dispatch policy. Tests: `CASE-QSC004-N1-RESERVE`, `CASE-QSC004-RESERVE-STORAGE-ONLY`, `CASE-QSC004-RESERVE-STORAGE-ENERGY`, and `CASE-QSC004-RESERVE-SHORTFALL`.
5. `JSON-05`: exact object schemas, duplicate-member rejection, and the distinction between JSON booleans and integers. Tests: `CASE-QSC004-REJECT-DUPLICATE-MEMBER`, `CASE-QSC004-REJECT-BOOLEAN-HORIZON`, and `CASE-QSC004-REJECT-BOOLEAN-DURATION`.

The expected values are checked from the public equations, hand calculations, and exhaustive enumeration of all voluntary commitment matrices within the public 2-generator/6-period bounds. Deterministic ordering, exact output shape, commitment accounting, and atomic rejection are additional contract-integrity checks rather than separate domain-difficulty axes.

The global objective includes marginal generation cost, startup cost, and the stated unserved-energy penalty. The per-hour allocation among committed units follows the public merit-order rule; the horizon search selects the commitment matrix that minimizes the resulting complete ledger while satisfying ramp, duration, storage, and reserve constraints. Serialization, stable reruns, and boundary-only checks protect the handoff but do not replace these domain decisions.

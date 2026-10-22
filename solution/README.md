# Reference solution coverage

The reference implementation is intentionally independent of the verifier and covers four domain axes:

1. Commitment-duration state: minimum up/down intervals and initial state transitions. Tests: `test_minimum_up_duration_is_respected`, `test_initial_off_state_honors_minimum_down_duration`.
2. Inter-hour ramp feasibility: initial and adjacent ramp bounds constrain output. Test: `test_ramp_limits_include_initial_transition`.
3. Storage physics: charge/discharge efficiencies and capacity recursion preserve energy units. Tests: `test_storage_recurrence_uses_efficiencies`, `test_storage_capacity_is_never_exceeded`.
4. Renewable dispatch economics and conservation: renewable-first use, curtailment, unserved penalty, and exact balance. Tests: `test_renewable_is_used_before_thermal`, `test_unserved_load_is_last_resort_and_penalized`, `test_balance_residual_is_zero`.

The public contract also requires deterministic ordering, exact output shape, commitment accounting, and atomic rejection of malformed or late-invalid input. These are checked by the remaining behavior tests. Isolated fault review targets removing the initial ramp limit, reversing storage efficiency, ignoring minimum-down state, and publishing before late validation; each fault is expected to fail its mapped tests.

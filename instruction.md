# Renewable microgrid dispatch ledger

Implement `/app/microgrid.py` and make it executable through:

```text
python3 /app/microgrid.py INPUT.json OUTPUT.json
```

The input is UTF-8 JSON with `horizon_hours`, `generators`, `storage`, and `periods`. Each period has `load_MW` and `renewable_MW`. A generator has `id`, `min_MW`, `max_MW`, `marginal_cost`, `startup_cost`, `ramp_up_MW`, `ramp_down_MW`, `min_up_hours`, `min_down_hours`, and `initial_state` (`on` or `off`). The storage object has `capacity_MWh`, `initial_MWh`, `max_charge_MW`, `max_discharge_MW`, `charge_efficiency`, and `discharge_efficiency`.

Each storage efficiency must be greater than zero and at most one.

Return exactly `dispatch` and `summary`. `dispatch` contains one record per period in input order with generator records (`id`, `on`, `power_MW`), storage fields (`charge_MW`, `discharge_MW`, `state_MWh`), `renewable_used_MW`, `curtailment_MW`, `unserved_MW`, and `balance_residual_MW`. `summary` contains total cost, total unserved energy, total renewable curtailment, final storage state, and a per-generator `commitment_hours` mapping.

The initial state is the state at the start of the first hour, with zero elapsed time in that state. Apply the minimum up/down duration from that point, including the first hour. Each hourly commitment must also respect its ramp limits. Units that must stay on because of their minimum up time or ramp-down limit remain committed. When selecting additional output, use merit order by `(marginal_cost, id)` and do not start a unit whose minimum feasible output exceeds the remaining deficit. Report startup cost once when a unit changes from off to on; total cost is marginal generation cost plus startup cost plus the unserved-load penalty, not an optimization objective.

For each hour, renewable energy serves load first. Use remaining renewable surplus to charge storage within its power and energy limits, then curtail any unused renewable energy. When renewable supply is insufficient, dispatch feasible thermal output in merit order, then discharge available storage within its power and energy limits, and record any remaining deficit as unserved load. A must-run thermal minimum that exceeds the deficit may be absorbed by available storage charging capacity; if the resulting surplus cannot be absorbed while satisfying the storage limits, reject the input as infeasible and preserve the output path. Do not report negative charge, discharge, unserved load, or storage energy. Preserve input order in the result and use deterministic tie handling.

Reject malformed, non-finite, negative, inconsistent, or horizon-violating inputs with a nonzero exit and leave `OUTPUT.json` absent or byte-for-byte unchanged. Validate the complete record before publishing any output. Numeric fields must be finite; residual magnitude must be at most `1e-9` MW and storage state at most `1e-9` MWh from the stated recurrence. Re-running the same valid input must be idempotent and produce the same JSON bytes; an invalid run must not leave a temporary file beside the destination. The implementation must handle newly constructed valid systems, not a single fixture.

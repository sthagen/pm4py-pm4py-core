# Reset/inhibitor Petri-net examples

This directory contains seven bounded workflow nets that use both a reset arc
and an inhibitor arc. Each model has 15 visible activities. The corresponding
`logs/*.xes` files contain 30 traces produced by PM4Py's basic Petri-net
playout with `InhibitorResetSemantics`.

| Model | Why reset and inhibitor arcs are useful |
| --- | --- |
| `hospital_discharge` | Multiple clinical discrepancies can be cleared together; direct discharge is blocked while any remain. |
| `cyber_incident_response` | Containment clears accumulated threat indicators; recovery is blocked while an indicator is active. |
| `insurance_claim` | Special investigation clears all claim flags; straight-through approval requires an empty flag set. |
| `manufacturing_batch` | Batch rework clears all defect tokens; release is blocked while defects remain. |
| `loan_underwriting` | Committee review clears accumulated exceptions; automatic approval requires no exceptions. |
| `order_fulfillment` | Substitution clears all backorders; normal allocation is blocked while a backorder remains. |
| `emergency_evacuation` | An all-clear sweep clears active hazards; completion is blocked while hazards remain. |

Every process includes a parallel section after its reset/inhibitor decision
and an optional final revision loop. The generated traces are checked for:

- the expected domain activity ordering;
- correct ordering inside both parallel branches;
- successful replay with reset/inhibitor semantics;
- examples that exercise both the reset route and inhibitor-controlled route;
- a zero-cost semantics-aware Dijkstra alignment for every trace.

Regenerate and validate all artifacts from the repository root with:

```bash
python tests/input_data/inh_res_nets/generate_and_validate.py
```

The semantics-aware Dijkstra variant can also be called directly:

```python
from pm4py.algo.conformance.alignments.petri_net import algorithm
from pm4py.objects.petri_net.inhibitor_reset.semantics import (
    InhibitorResetSemantics,
)

result = algorithm.apply(
    log,
    net,
    initial_marking,
    final_marking,
    variant=algorithm.Variants.VERSION_DIJKSTRA_SEMANTICS,
    parameters={"petri_semantics": InhibitorResetSemantics()},
)
```

import pm4py


def execute_script():
    # OCEL OLAP operations introduced in:
    #   Khayatbashi, Miri & Jalali, "Advancing Object-Centric Process
    #   Mining with Multi-Dimensional Data Operations",
    #   CAiSE Forum 2025 (arXiv:2412.00393).
    # Two granularity axes are demonstrated below:
    #   * object-type granularity:  drill_down  <->  roll_up
    #   * event-type granularity:   unfold      <->  fold
    ocel = pm4py.read_ocel("../tests/input_data/ocel/example_log.jsonocel")

    print("=== Original OCEL ===")
    print("Object types:", pm4py.ocel_get_object_types(ocel))
    print(ocel.objects[["ocel:oid", "ocel:type", "oattr1"]])

    # --- Drill-down -----------------------------------------------------
    # Use case: an analyst notices that the object type "element"
    # actually covers heterogeneous sub-populations distinguished by the
    # "oattr1" attribute, and wants to study them separately. Drill-down
    # rewrites the type of each "element" object to "(element, <value>)".
    # Objects whose attribute value is undefined (e.g. NaN) keep the
    # original type.
    ocel_dd = pm4py.ocel_drill_down(ocel, object_type="element", object_attribute="oattr1")
    print("\n=== After drill_down on (element, oattr1) ===")
    print("Object types:", pm4py.ocel_get_object_types(ocel_dd))

    # Concrete impact: the discovered OC-DFG now distinguishes the
    # sub-populations that were fused together in the original log.
    ocdfg_before = pm4py.discover_ocdfg(ocel)
    ocdfg_after = pm4py.discover_ocdfg(ocel_dd)
    print("OC-DFG object types before:", sorted(ocdfg_before["object_types"]))
    print("OC-DFG object types after :", sorted(ocdfg_after["object_types"]))

    # --- Roll-up --------------------------------------------------------
    # Use case: undo a previous drill-down once the sub-population
    # analysis is complete, or aggregate granular types back into a
    # coarser parent type for a higher-level view.
    ocel_ru = pm4py.ocel_roll_up(ocel_dd, object_type="element")
    print("\n=== After roll_up back to element ===")
    print("Object types:", pm4py.ocel_get_object_types(ocel_ru))
    print("drill_down -> roll_up round-trip equal to original?", ocel_ru == ocel)

    # --- Unfold ---------------------------------------------------------
    # Use case: a single event type (here "Create Order") interacts with
    # multiple object types, and the analyst wants the discovered model
    # to distinguish the event's behaviour per related object type.
    # Unfold rewrites the activity of matching events to
    # "(Create Order, order)". An optional `qualifiers=[...]` argument
    # restricts the split to events whose driving E2O relation carries
    # one of the listed qualifier values.
    ocel_uf = pm4py.ocel_unfold(ocel, event_type="Create Order", object_type="order")
    print("\n=== After unfold of (Create Order, order) ===")
    print("Activities:", sorted(ocel_uf.events["ocel:activity"].unique()))

    # --- Fold -----------------------------------------------------------
    # Use case: undo an earlier unfold, restoring the original event
    # type "Create Order" in both events and E2O relations.
    ocel_fo = pm4py.ocel_fold(ocel_uf, event_type="Create Order", object_type="order")
    print("\n=== After fold back to Create Order ===")
    print("Activities:", sorted(ocel_fo.events["ocel:activity"].unique()))
    print("unfold -> fold round-trip equal to original?", ocel_fo == ocel)


if __name__ == "__main__":
    execute_script()

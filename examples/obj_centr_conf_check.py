import pm4py
from pm4py.objects.ocel.obj import OCEL
from typing import Any


def execute_script():
    ocel: OCEL = pm4py.read_ocel("../tests/input_data/ocel/ocel_order_simulated.csv")

    # subset that we consider as normative
    ocel1: OCEL = pm4py.sample_ocel_connected_components(ocel, 1)
    # subset that we use to extract the 'normative' behavior
    ocel2: OCEL = pm4py.sample_ocel_connected_components(ocel, 1)

    # object-centric DFG from OCEL2
    ocdfg2: dict[str, Any] = pm4py.discover_ocdfg(ocel2)
    # OTG (object-type-graph) from OCEL2
    otg2: tuple[set[str], dict[tuple[str, str, str], int]] = pm4py.discover_otg(ocel2)
    # ETOT (ET-OT graph) from OCEL2
    etot2: tuple[set[str], set[str], set[tuple[str, str]], dict[tuple[str, str], int]] = pm4py.discover_etot(ocel2)

    # conformance checking
    print("== OCDFG")
    diagn_ocdfg: dict[str, Any] = pm4py.conformance_ocdfg(ocel1, ocdfg2)
    print(diagn_ocdfg)

    print("\n\n== OTG")
    diagn_otg: dict[str, Any] = pm4py.conformance_otg(ocel1, otg2)
    print(diagn_otg)

    print("\n\n== ETOT")
    diagn_etot: dict[str, Any] = pm4py.conformance_etot(ocel1, etot2)
    print(diagn_etot)


if __name__ == "__main__":
    execute_script()

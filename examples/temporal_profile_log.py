import pm4py
from pm4py.algo.discovery.temporal_profile import algorithm as temporal_profile_discovery
from pm4py.algo.conformance.temporal_profile import algorithm as temporal_profile_conformance


def execute_script():
    log: "pandas.DataFrame" = pm4py.read_xes("../tests/input_data/receipt.xes")
    tf: "dict[tuple[str, str], tuple[float, float]]" = temporal_profile_discovery.apply(log)
    conformance: "list[list[tuple[float, float, float, float]]]" = temporal_profile_conformance.apply(log, tf, parameters={"zeta": 6.0})
    for index, dev in enumerate(conformance):
        if len(dev) > 0:
            print(index, dev)


if __name__ == "__main__":
    execute_script()

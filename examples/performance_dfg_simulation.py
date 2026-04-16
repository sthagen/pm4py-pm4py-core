import os

import pm4py
from pm4py.algo.simulation.playout.dfg import algorithm as dfg_simulator


def execute_script():
    log: "pandas.DataFrame" = pm4py.read_xes(os.path.join("..", "tests", "input_data", "receipt.xes"))
    frequency_dfg: "dict"
    sa: "dict"
    ea: "dict"
    frequency_dfg, sa, ea = pm4py.discover_dfg(log)
    performance_dfg: "dict"
    performance_dfg, sa, ea = pm4py.discover_performance_dfg(log)
    simulated_log = dfg_simulator.apply(frequency_dfg, sa, ea, variant=dfg_simulator.Variants.PERFORMANCE,
                                        parameters={"performance_dfg": performance_dfg})
    print(simulated_log)


if __name__ == "__main__":
    execute_script()

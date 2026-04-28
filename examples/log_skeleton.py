from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.algo.discovery.log_skeleton import algorithm as lsk
from pm4py.algo.conformance.log_skeleton import algorithm as lsk_conf
import os
from pm4py.objects.log.obj import EventLog
from typing import Any


def execute_script():
    log: EventLog = xes_importer.apply(os.path.join("..", "tests", "input_data", "receipt.xes"))
    # discovers the log skeleton with a minimal noise
    log_skeleton: dict[str, Any] = lsk.apply(log, parameters={lsk.Variants.CLASSIC.value.Parameters.NOISE_THRESHOLD: 0.01})
    print(log_skeleton)
    # applies conformance checking to it
    results: list[set[Any]] = lsk_conf.apply(log, log_skeleton)
    for i in range(min(len(results), 5)):
        # print the i-the conformance checking
        print(results[i])


if __name__ == "__main__":
    execute_script()

from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.algo.conformance.tokenreplay import algorithm as tr
from pm4py.objects.conversion.process_tree import converter as process_tree_converter
import os
from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.process_tree.obj import ProcessTree
from typing import Any


def execute_script():
    log: EventLog = xes_importer.apply(os.path.join("..", "tests", "input_data", "running-example.xes"))
    process_tree: ProcessTree = inductive_miner.apply(log)
    net: PetriNet
    im: Marking
    fm: Marking
    net, im, fm = process_tree_converter.apply(process_tree)
    # perform the backwards token-based replay
    replayed_traces: list[dict[str, Any]] = tr.apply(log, net, im, fm, variant=tr.Variants.BACKWARDS)
    print(replayed_traces)


if __name__ == "__main__":
    execute_script()

import os

from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.algo.evaluation import algorithm as general_evaluation
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.conversion.process_tree import converter as process_tree_converter


def execute_script():
    log: "EventLog" = xes_importer.apply(os.path.join("..", "tests", "input_data", "reviewing.xes"))
    process_tree: "ProcessTree" = inductive_miner.apply(log)
    net: "PetriNet"
    marking: "Marking"
    final_marking: "Marking"
    net, marking, final_marking = process_tree_converter.apply(process_tree)
    metrics: "dict[str, float]" = general_evaluation.apply(log, net, marking, final_marking)
    print("metrics=", metrics)


if __name__ == "__main__":
    execute_script()

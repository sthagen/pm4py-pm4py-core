import os
from pm4py.objects.log.importer.xes import importer
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
from pm4py.objects.conversion.process_tree import converter as process_tree_converter
from examples import examples_conf
import importlib.util
from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.process_tree.obj import ProcessTree
from typing import Any


def execute_script():
    log: EventLog = importer.apply(os.path.join("..", "tests", "input_data", "running-example.xes"))
    process_tree: ProcessTree = inductive_miner.apply(log)
    net: PetriNet
    im: Marking
    fm: Marking
    net, im, fm = process_tree_converter.apply(process_tree)
    aligned_traces: dict[str, Any] | list[dict[str, Any]] = alignments.apply(log, net, im, fm)

    if importlib.util.find_spec("graphviz"):
        from pm4py.visualization.align_table import visualizer
        gviz = visualizer.apply(log, aligned_traces,
                                parameters={visualizer.Variants.CLASSIC.value.Parameters.FORMAT: examples_conf.TARGET_IMG_FORMAT})
        visualizer.view(gviz)


if __name__ == "__main__":
    execute_script()

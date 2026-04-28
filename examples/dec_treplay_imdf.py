import os

from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.conversion.process_tree import converter as process_tree_converter
from examples import examples_conf
import importlib.util
from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.process_tree.obj import ProcessTree
from typing import Any


def execute_script():
    # import the log
    log_path: str = os.path.join("..", "tests", "input_data", "receipt.xes")
    log: EventLog = xes_importer.apply(log_path)
    # apply Inductive Miner
    process_tree: ProcessTree = inductive_miner.apply(log)
    net: PetriNet
    initial_marking: Marking
    final_marking: Marking
    net, initial_marking, final_marking = process_tree_converter.apply(process_tree)

    if importlib.util.find_spec("graphviz"):
        from pm4py.visualization.petri_net import visualizer as pn_vis
        # get visualization
        variant = pn_vis.Variants.PERFORMANCE
        parameters_viz: dict[Any, str] = {pn_vis.Variants.PERFORMANCE.value.Parameters.AGGREGATION_MEASURE: "mean", pn_vis.Variants.PERFORMANCE.value.Parameters.FORMAT: examples_conf.TARGET_IMG_FORMAT}
        gviz = pn_vis.apply(net, initial_marking, final_marking, log=log, variant=variant,
                            parameters=parameters_viz)
        pn_vis.view(gviz)
        # do another visualization with frequency
        variant = pn_vis.Variants.FREQUENCY
        parameters_viz = {pn_vis.Variants.FREQUENCY.value.Parameters.FORMAT: examples_conf.TARGET_IMG_FORMAT}
        gviz = pn_vis.apply(net, initial_marking, final_marking, log=log, variant=variant,
                            parameters=parameters_viz)
        pn_vis.view(gviz)


if __name__ == "__main__":
    execute_script()

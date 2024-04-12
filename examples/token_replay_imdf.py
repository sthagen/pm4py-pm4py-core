import os

from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.conversion.process_tree import converter as process_tree_converter
from examples import examples_conf
import importlib.util


def execute_script():
    log_path = os.path.join("..", "tests", "input_data", "running-example.xes")
    log = xes_importer.apply(log_path)
    print("loaded log")
    process_tree = inductive_miner.apply(log)
    net, marking, final_marking = process_tree_converter.apply(process_tree)
    for place in marking:
        print("initial marking " + place.name)
    for place in final_marking:
        print("final marking " + place.name)

    if importlib.util.find_spec("graphviz"):
        from pm4py.visualization.petri_net import visualizer as pn_vis
        gviz = pn_vis.apply(net, marking, final_marking,
                            parameters={pn_vis.Variants.WO_DECORATION.value.Parameters.FORMAT: examples_conf.TARGET_IMG_FORMAT})
        pn_vis.view(gviz)

    print("started token replay")
    aligned_traces = token_replay.apply(log, net, marking, final_marking)
    fit_traces = [x for x in aligned_traces if x['trace_is_fit']]
    perc_fitness = 0.00
    if len(aligned_traces) > 0:
        perc_fitness = len(fit_traces) / len(aligned_traces)
    print("perc_fitness=", perc_fitness)


if __name__ == "__main__":
    execute_script()

import os
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.algo.comparison.petrinet import element_usage_comparison
from pm4py.objects.log.util import sorting
from pm4py.objects.log.obj import EventLog
from pm4py.objects.conversion.process_tree import converter as process_tree_converter
from examples import examples_conf
import importlib.util


def execute_script():
    log = xes_importer.apply(os.path.join("..", "tests", "input_data", "receipt.xes"))
    log = sorting.sort_timestamp(log)
    process_tree = inductive_miner.apply(log)
    net, im, fm = process_tree_converter.apply(process_tree)
    log1 = EventLog(log[:500])
    log2 = EventLog(log[len(log) - 500:])
    statistics = element_usage_comparison.compare_element_usage_two_logs(net, im, fm, log1, log2)

    if importlib.util.find_spec("graphviz"):
        from pm4py.visualization.petri_net import visualizer as pn_vis
        gviz = pn_vis.apply(net, im, fm, variant=pn_vis.Variants.FREQUENCY, aggregated_statistics=statistics,
                            parameters={pn_vis.Variants.FREQUENCY.value.Parameters.FORMAT: examples_conf.TARGET_IMG_FORMAT})
        pn_vis.view(gviz)


if __name__ == "__main__":
    execute_script()

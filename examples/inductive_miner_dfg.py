import pm4py
import os
from pm4py.objects.dfg.obj import DFG
from examples import examples_conf
import importlib.util


def execute_script():
    log = pm4py.read_xes(os.path.join("..", "tests", "input_data", "running-example.xes"), return_legacy_log_object=False)
    typed_dfg_1 = pm4py.discover_dfg_typed(log)
    # in alternative ...
    dfg, sa, ea = pm4py.discover_dfg(log)
    typed_dfg_2 = DFG(dfg, sa, ea)

    tree = pm4py.discover_process_tree_inductive(typed_dfg_2, noise_threshold=0.2)
    net, im, fm = pm4py.convert_to_petri_net(tree)

    if importlib.util.find_spec("graphviz"):
        pm4py.view_process_tree(tree, format=examples_conf.TARGET_IMG_FORMAT)
        pm4py.view_petri_net(net, im, fm, format=examples_conf.TARGET_IMG_FORMAT)


if __name__ == "__main__":
    execute_script()

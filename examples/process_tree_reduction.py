import pm4py
import os
from pm4py.algo.reduction.process_tree import reducer
from pm4py.objects.log.importer.xes import importer as xes_importer
from examples import examples_conf
import importlib.util


def execute_script():
    log = xes_importer.apply(os.path.join("..", "tests", "input_data", "receipt.xes"))
    # the tree discovered by inductive miner is huge and can replay the behavior of the log
    tree = pm4py.discover_process_tree_inductive(log)
    # to make a more effective replay, remove the elements that are not being used during the replay of the trace
    # (that are the skippable ones, with empty intersection with the trace)
    tree_first_trace = reducer.apply(tree, log[0], variant=reducer.Variants.TREE_TR_BASED)

    if importlib.util.find_spec("graphviz"):
        pm4py.view_process_tree(tree, examples_conf.TARGET_IMG_FORMAT)
        pm4py.view_process_tree(tree_first_trace, examples_conf.TARGET_IMG_FORMAT)
        # much smaller, isn't it? :)


if __name__ == "__main__":
    execute_script()

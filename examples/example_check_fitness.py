import time

import pm4py
from pm4py.objects.log.util import filtering_utils


def execute_script():
    log: "pandas.DataFrame" = pm4py.read_xes("../tests/compressed_input_data/02_teleclaims.xes.gz")
    tree: "ProcessTree" = pm4py.discover_process_tree_inductive(log, noise_threshold=0.3)
    net: "PetriNet"
    im: "Marking"
    fm: "Marking"
    net, im, fm = pm4py.convert_to_petri_net(tree)
    # reduce the log to one trace per variant
    log = filtering_utils.keep_one_trace_per_variant(log)
    for index, trace in enumerate(log):
        print(index)
        aa: "float" = time.time()
        check_tree: "bool" = pm4py.check_is_fitting(trace, tree)
        bb: "float" = time.time()
        check_petri: "bool" = pm4py.check_is_fitting(trace, net, im, fm)
        cc: "float" = time.time()
        print("check on tree: ", check_tree, "time", bb - aa)
        print("check on Petri net: ", check_petri, "time", cc - bb)
        print()


if __name__ == "__main__":
    execute_script()

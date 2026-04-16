import os
import time

import pm4py
from pm4py.algo.conformance.alignments.petri_net import algorithm as petri_alignments
from pm4py.algo.filtering.dfg import dfg_filtering
from pm4py.algo.conformance.alignments.dfg import algorithm as dfg_alignment
from pm4py.statistics.attributes.log import get
from pm4py.objects.petri_net.utils import align_utils
from examples import examples_conf
import importlib.util


def execute_script():
    log: "pandas.DataFrame" = pm4py.read_xes(os.path.join("..", "tests", "input_data", "receipt.xes"))
    print("number of cases", len(log))
    print("number of events", sum(len(x) for x in log))
    print("number of variants", len(pm4py.get_variants_as_tuples(log)))
    ac: "dict[Any, int]" = get.get_attribute_values(log, "concept:name")
    dfg: "dict"
    sa: "dict"
    ea: "dict"
    dfg, sa, ea = pm4py.discover_dfg(log)
    perc: "float" = 0.5
    dfg, sa, ea, ac = dfg_filtering.filter_dfg_on_activities_percentage(dfg, sa, ea, ac, perc)
    dfg, sa, ea, ac = dfg_filtering.filter_dfg_on_paths_percentage(dfg, sa, ea, ac, perc)
    aa: "float" = time.time()
    aligned_traces: "dict[str, Any] | list[dict[str, Any]]" = dfg_alignment.apply(log, dfg, sa, ea)
    bb: "float" = time.time()
    net: "PetriNet"
    im: "Marking"
    fm: "Marking"
    net, im, fm = pm4py.convert_to_petri_net(dfg, sa, ea)
    for trace in aligned_traces:
        if trace["cost"] != trace["internal_cost"]:
            print(trace)
            pass
    print(bb - aa)
    print(sum(x["visited_states"] for x in aligned_traces))
    print(sum(x["cost"] // align_utils.STD_MODEL_LOG_MOVE_COST for x in aligned_traces))

    if importlib.util.find_spec("graphviz"):
        from pm4py.visualization.dfg import visualizer
        gviz = visualizer.apply(dfg, activities_count=ac, parameters={"start_activities": sa, "end_activities": ea,
                                                                      "format": examples_conf.TARGET_IMG_FORMAT})
        visualizer.view(gviz)

    cc: "float" = time.time()
    aligned_traces2 = petri_alignments.apply(log, net, im, fm,
                                             variant=petri_alignments.Variants.VERSION_DIJKSTRA_LESS_MEMORY)
    dd: "float" = time.time()
    print(dd - cc)
    print(sum(x["visited_states"] for x in aligned_traces2))
    print(sum(x["cost"] // align_utils.STD_MODEL_LOG_MOVE_COST for x in aligned_traces2))


if __name__ == "__main__":
    execute_script()

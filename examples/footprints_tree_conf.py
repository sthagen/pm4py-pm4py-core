from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.algo.discovery.footprints import algorithm as fp_discovery
from pm4py.algo.conformance.footprints import algorithm as fp_conformance
from pm4py.statistics.traces.generic.log import case_statistics
from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
from pm4py.algo.filtering.log.paths import paths_filter
from pm4py.util.vis_utils import human_readable_stat
from pm4py.algo.filtering.log.variants import variants_filter
from pm4py.statistics.variants.log import get as variants_get
from examples import examples_conf
import os
import importlib.util


def execute_script():
    log: "EventLog" = xes_importer.apply(os.path.join("..", "tests", "input_data", "receipt.xes"))
    throughput_time = case_statistics.get_median_case_duration(log)
    variants: "dict[list[str], list[Trace]] | dict[str, list[Trace]]"
    variants_times: "dict[list[str], numpy.ndarray] | dict[str, numpy.ndarray]"
    variants, variants_times = variants_get.get_variants_along_with_case_durations(log)
    dfg: "dict[tuple[str, str], float]" = dfg_discovery.apply(log)
    filtered_log = variants_filter.filter_log_variants_percentage(log, 0.2)
    # filtered_log = log
    tree: "ProcessTree" = inductive_miner.apply(filtered_log)
    fp_log: "dict[str, Any]" = fp_discovery.apply(log, variant=fp_discovery.Variants.ENTIRE_EVENT_LOG)
    fp_model: "dict[str, Any]" = fp_discovery.apply(tree)
    conf: "list[dict[str, Any]] | dict[str, Any]" = fp_conformance.apply(fp_log, fp_model)
    conf_occ = sorted([(x, dfg[x]) for x in conf], key=lambda y: (y[1], y[0][0], y[0][1]), reverse=True)
    print(
        "source activity\t\ttarget activity\t\toccurrences\t\tthroughput time log\t\tthroughput time traces with path")
    for i in range(min(10, len(conf_occ))):
        path = conf_occ[i][0]
        occ = conf_occ[i][1]
        red_log: "EventLog" = paths_filter.apply(log, [path])
        red_throughput_time = case_statistics.get_median_case_duration(red_log)
        print("%s\t\t%s\t\t%d\t\t%s\t\t%s" % (
            path[0], path[1], occ, human_readable_stat(throughput_time), human_readable_stat(red_throughput_time)))
    variants_length = sorted([(x, len(variants[x])) for x in variants.keys()], key=lambda y: (y[1], y[0]), reverse=True)
    print("\nvariant\t\toccurrences\t\tthroughput time log\t\tthroughput time traces with path")
    for i in range(min(10, len(variants_length))):
        var = variants_length[i][0]
        vark: "str" = str(var)
        if len(vark) > 10:
            vark = vark[:10]
        occ = variants_length[i][1]
        fp_log_var: "dict[str, Any]" = fp_discovery.apply(variants[var], variant=fp_discovery.Variants.ENTIRE_EVENT_LOG)
        conf_var: "list[dict[str, Any]] | dict[str, Any]" = fp_conformance.apply(fp_log_var, fp_model)
        is_fit: "str" = str(len(conf_var) == 0)
        var_throughput = case_statistics.get_median_case_duration(variants[var])
        print("%s\t\t%d\t\t%s\t\t%s\t\t%s" % (vark, occ, is_fit, throughput_time, human_readable_stat(var_throughput)))


    if importlib.util.find_spec("graphviz"):
        from pm4py.algo.conformance.footprints.util import tree_visualization
        from pm4py.visualization.process_tree import visualizer as pt_visualizer
        # print(conf_occ)
        conf_colors = tree_visualization.apply(tree, conf)
        if True:
            gviz = pt_visualizer.apply(tree, parameters={"format": examples_conf.TARGET_IMG_FORMAT,
                                                         pt_visualizer.Variants.WO_DECORATION.value.Parameters.COLOR_MAP: conf_colors,
                                                         pt_visualizer.Variants.WO_DECORATION.value.Parameters.ENABLE_DEEPCOPY: False})
            pt_visualizer.view(gviz)


if __name__ == "__main__":
    execute_script()

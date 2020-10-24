import os, sys
sys.path.append("/Users/Julian/Documents/HiWi/PADS/pm4py-source")

from pm4py.objects.log.importer.xes import importer as xes_import
from pm4py.algo.discovery.inductive import algorithm as ind_miner
from pm4py.visualization.process_tree import visualizer as pt_vis
from pm4py.visualization.petrinet import visualizer as pn_vis
from pm4py.objects.conversion.process_tree import converter
from pm4py.evaluation.replay_fitness import evaluator
from pm4py.algo.discovery.inductive.variants.im.util import fall_through
from pm4py.algo.discovery.inductive.variants.im.util import constants as inductive_consts
from pm4py.algo.discovery.inductive.parameters import Parameters
from pm4py.statistics.variants.log import get as variants_module
from pm4py.objects.log.log import EventLog


def keep_one_trace_per_variant(log, parameters=None):
    """
    Keeps only one trace per variant (does not matter for basic inductive miner)

    Parameters
    --------------
    log
        Log
    parameters
        Parameters of the algorithm

    Returns
    --------------
    new_log
        Log (with one trace per variant)
    """
    if parameters is None:
        parameters = {}

    variants = variants_module.get_variants(log, parameters=parameters)
    new_log = EventLog()
    for var in variants:
        new_log.append(variants[var][0])

    return new_log


def execute_script():
    log_path = os.path.join("/Users/Julian/Documents/HiWi/PADS/EventLogs/BPI_Challenge_2012.xes")
    log = xes_import.apply(log_path)
    #log = keep_one_trace_per_variant(log)
    #log = log[15:30]
    ptree = ind_miner.apply_tree(log, parameters={Parameters.NOISE_THRESHOLD: 0.5}, variant=ind_miner.Variants.IMf)
    gviz = pt_vis.apply(ptree,
                        parameters={pt_vis.Variants.WO_DECORATION.value.Parameters.FORMAT: "svg"})


    net, im, fm = converter.apply(ptree)

    pt_vis.view(gviz)
   print(evaluator.apply(log, net, im, fm, variant=evaluator.Variants.TOKEN_BASED))


if __name__ == "__main__":
    execute_script()
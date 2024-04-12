import os

from pm4py.algo.discovery.heuristics import algorithm as heuristics_miner
from pm4py.objects.log.importer.xes import importer as xes_importer
from examples import examples_conf
import importlib.util


def execute_script():
    log = xes_importer.apply(os.path.join("..", "tests", "compressed_input_data", "09_a32f0n00.xes.gz"))
    heu_net = heuristics_miner.apply_heu(log, parameters={
        heuristics_miner.Variants.CLASSIC.value.Parameters.DEPENDENCY_THRESH: 0.99})

    if importlib.util.find_spec("pydotplus") and importlib.util.find_spec("graphviz"):
        from pm4py.visualization.heuristics_net import visualizer as hn_vis
        gviz = hn_vis.apply(heu_net, parameters={hn_vis.Variants.PYDOTPLUS.value.Parameters.FORMAT: examples_conf.TARGET_IMG_FORMAT})
        hn_vis.view(gviz)

    net, im, fm = heuristics_miner.apply(log, parameters={
        heuristics_miner.Variants.CLASSIC.value.Parameters.DEPENDENCY_THRESH: 0.99})

    if importlib.util.find_spec("graphviz"):
        from pm4py.visualization.petri_net import visualizer as petri_vis
        gviz2 = petri_vis.apply(net, im, fm, parameters={petri_vis.Variants.WO_DECORATION.value.Parameters.FORMAT: examples_conf.TARGET_IMG_FORMAT})
        petri_vis.view(gviz2)


if __name__ == "__main__":
    execute_script()

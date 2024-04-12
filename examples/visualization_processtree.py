from pm4py.objects.log.importer.xes import importer
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from examples import examples_conf
import os
import importlib.util


def execute_script():
    log = importer.apply(os.path.join("..", "tests", "input_data", "running-example.xes"))
    tree = inductive_miner.apply(log)

    if importlib.util.find_spec("graphviz"):
        from pm4py.visualization.process_tree import visualizer as pt_vis_factory
        from pm4py.visualization.process_tree import visualizer as pt_visualizer

        gviz1 = pt_vis_factory.apply(tree, parameters={"format": examples_conf.TARGET_IMG_FORMAT})
        # pt_vis_factory.view(gviz1)
        gviz2 = pt_visualizer.apply(tree, parameters={pt_visualizer.Variants.WO_DECORATION.value.Parameters.FORMAT: examples_conf.TARGET_IMG_FORMAT})
        pt_visualizer.view(gviz2)


if __name__ == "__main__":
    execute_script()

import pm4py
import os
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.util.compression.dtypes import UVCL
from pm4py.algo.discovery.inductive.variants.imf import IMFUVCL
from pm4py.algo.discovery.inductive.dtypes.im_ds import IMDataStructureUVCL
from examples import examples_conf
import importlib.util


def execute_script():
    log = pm4py.read_xes(os.path.join("..", "tests", "input_data", "running-example.xes"), return_legacy_log_object=False)
    variants = pm4py.get_variants(log)
    uvcl = UVCL()
    for var, occ in variants.items():
        uvcl[var] = occ
    parameters = {"noise_threshold": 0.2}
    imfuvcl = IMFUVCL(parameters)

    tree = imfuvcl.apply(IMDataStructureUVCL(uvcl), parameters=parameters)
    net, im, fm = pm4py.convert_to_petri_net(tree)

    if importlib.util.find_spec("graphviz"):
        pm4py.view_process_tree(tree, format=examples_conf.TARGET_IMG_FORMAT)
        pm4py.view_petri_net(net, im, fm, format=examples_conf.TARGET_IMG_FORMAT)


if __name__ == "__main__":
    execute_script()

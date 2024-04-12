import pm4py
from pm4py.algo.discovery.ocel.saw_nets import algorithm as saw_nets_disc
from pm4py.objects.petri_net.obj import Marking
from examples import examples_conf
import importlib.util


def execute_script():
    ocel = pm4py.read_ocel("../tests/input_data/ocel/ocel_order_simulated.csv")
    res = saw_nets_disc.apply(ocel)

    if importlib.util.find_spec("graphviz"):
        for ot in res["ot_saw_nets"]:
            pm4py.view_petri_net(res["ot_saw_nets"][ot], Marking(), Marking(), format=examples_conf.TARGET_IMG_FORMAT)
        pm4py.view_petri_net(res["multi_saw_net"], Marking(), Marking(), decorations=res["decorations_multi_saw_net"],
                             format=examples_conf.TARGET_IMG_FORMAT)


if __name__ == "__main__":
    execute_script()

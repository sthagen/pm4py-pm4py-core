import pm4py
from examples import examples_conf
import os
import importlib.util
from pm4py.objects.ocel.obj import OCEL
from pm4py.objects.ocpn.obj import OCPetriNet


def execute_script():
    ocel: OCEL = pm4py.read_ocel(os.path.join("..", "tests", "input_data", "ocel", "example_log.jsonocel"))
    model: OCPetriNet = pm4py.discover_oc_petri_net(ocel)
    print(model.keys())

    if importlib.util.find_spec("graphviz"):
        pm4py.view_ocpn(model, format=examples_conf.TARGET_IMG_FORMAT)


if __name__ == "__main__":
    execute_script()

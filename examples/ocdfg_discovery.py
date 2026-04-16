import pm4py
from examples import examples_conf
import os
import importlib.util


def execute_script():
    ocel: "OCEL" = pm4py.read_ocel(os.path.join("..", "tests", "input_data", "ocel", "example_log.jsonocel"))
    ocdfg: "dict[str, Any]" = pm4py.discover_ocdfg(ocel)

    if importlib.util.find_spec("graphviz"):
        # views the model with the frequency annotation
        pm4py.view_ocdfg(ocdfg, format=examples_conf.TARGET_IMG_FORMAT)
        # views the model with the performance annotation
        pm4py.view_ocdfg(ocdfg, format=examples_conf.TARGET_IMG_FORMAT, annotation="performance", performance_aggregation="median")


if __name__ == "__main__":
    execute_script()

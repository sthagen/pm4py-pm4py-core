import pm4py
import importlib.util


def execute_script():
    log = pm4py.read_xes("../tests/input_data/running-example.xes")

    bpmn_model = pm4py.discover_bpmn_inductive(log)

    if importlib.util.find_spec("graphviz"):
        pm4py.view_bpmn(bpmn_model, variant_str="dagrejs")


if __name__ == "__main__":
    execute_script()

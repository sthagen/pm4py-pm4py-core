import pm4py
from examples import examples_conf
import importlib.util
import os


def execute_script():
    # reads a XES log
    log = pm4py.read_xes(os.path.join("..", "tests", "input_data", "receipt.xes"))

    if importlib.util.find_spec("graphviz"):
        # generates the default dotted chart (timestamp on X-axis, case ID on Y-axis, activity as color)
        pm4py.view_dotted_chart(log, format=examples_conf.TARGET_IMG_FORMAT)
        # generates the dotted chart with the activity on the X-axis, the resource on the Y-axis, and the group
        # as color
        pm4py.view_dotted_chart(log, format=examples_conf.TARGET_IMG_FORMAT, attributes=["concept:name", "org:resource", "org:group"])


if __name__ == "__main__":
    execute_script()

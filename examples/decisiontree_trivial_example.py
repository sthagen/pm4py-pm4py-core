import os

from pm4py.util import ml_utils
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.log.util import get_class_representation
from pm4py.algo.transformation.trace_encodings import algorithm as trace_encodings
from examples import examples_conf
import importlib.util
from pm4py.objects.log.obj import EventLog


def execute_script():
    log_path: str = os.path.join("..", "tests", "input_data", "roadtraffic50traces.xes")
    # log_path = os.path.join("..", "tests", "input_data", "receipt.xes")
    log: EventLog = xes_importer.apply(log_path)
    # now, it is possible to get a default representation of an event log
    feature_names: list[str]
    data, feature_names = trace_encodings.apply(log, variant=trace_encodings.Variants.TRACE_BASED)
    # gets classes representation by final concept:name value (end activity)
    target, classes = get_class_representation.get_class_representation_by_str_ev_attr_value_value(log, "concept:name")

    if importlib.util.find_spec("sklearn") and importlib.util.find_spec("graphviz"):
        # mine the decision tree given 'data' and 'target'
        clf = ml_utils.DecisionTreeClassifier(max_depth=7)
        clf.fit(data, target)

        # visualize the decision tree
        from pm4py.visualization.decisiontree import visualizer as dt_vis
        gviz = dt_vis.apply(clf, feature_names, classes, parameters={dt_vis.Variants.CLASSIC.value.Parameters.FORMAT: examples_conf.TARGET_IMG_FORMAT})
        dt_vis.view(gviz)

    # gets classes representation by trace duration (threshold between the two classes = 200D)
    target, classes = get_class_representation.get_class_representation_by_trace_duration(log, 2 * 8640000)

    if importlib.util.find_spec("sklearn") and importlib.util.find_spec("graphviz"):
        # mine the decision tree given 'data' and 'target'
        clf = ml_utils.DecisionTreeClassifier(max_depth=7)
        clf.fit(data, target)

        # visualize the decision tree
        from pm4py.visualization.decisiontree import visualizer as dt_vis
        gviz = dt_vis.apply(clf, feature_names, classes, parameters={dt_vis.Variants.CLASSIC.value.Parameters.FORMAT: examples_conf.TARGET_IMG_FORMAT})
        dt_vis.view(gviz)


if __name__ == "__main__":
    execute_script()

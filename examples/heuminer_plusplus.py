import pm4py
from pm4py.algo.discovery.heuristics.variants import plusplus
from pm4py.util import constants, pandas_utils
from pm4py.objects.log.util import dataframe_utils
from examples import examples_conf
import importlib.util


def execute_script():
    df = pandas_utils.read_csv("../tests/input_data/interval_event_log.csv")
    df = dataframe_utils.convert_timestamp_columns_in_df(df, timest_format=constants.DEFAULT_TIMESTAMP_PARSE_FORMAT, timest_columns=["start_timestamp", "time:timestamp"])
    log = pm4py.read_xes("../tests/input_data/interval_event_log.xes")
    heu_net = plusplus.apply_heu(log, parameters={"heu_net_decoration": "performance"})
    heu_net_2 = plusplus.apply_heu_pandas(df, parameters={"heu_net_decoration": "performance"})

    if importlib.util.find_spec("pydotplus") and importlib.util.find_spec("graphviz"):
        from pm4py.visualization.heuristics_net import visualizer
        gviz = visualizer.apply(heu_net, parameters={"format": examples_conf.TARGET_IMG_FORMAT})
        visualizer.view(gviz)
        gviz2 = visualizer.apply(heu_net_2, parameters={"format": examples_conf.TARGET_IMG_FORMAT})
        visualizer.view(gviz2)

    net1, im1, fm1 = plusplus.apply(log)
    net2, im2, fm2 = plusplus.apply(log)

    if importlib.util.find_spec("pydotplus") and importlib.util.find_spec("graphviz"):
        from pm4py.visualization.petri_net import visualizer as pn_visualizer
        gviz3 = pn_visualizer.apply(net1, im1, fm1, parameters={"format": examples_conf.TARGET_IMG_FORMAT})
        pn_visualizer.view(gviz3)
        gviz4 = pn_visualizer.apply(net2, im2, fm2, parameters={"format": examples_conf.TARGET_IMG_FORMAT})
        pn_visualizer.view(gviz4)


if __name__ == "__main__":
    execute_script()

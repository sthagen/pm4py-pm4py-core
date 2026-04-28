import pm4py
import networkx as nx
import os
import networkx
from pm4py.objects.ocel.obj import OCEL


def execute_script():
    ocel: OCEL = pm4py.read_ocel("../tests/input_data/ocel/example_log.jsonocel")
    nx_digraph: networkx.DiGraph = pm4py.convert_ocel_to_networkx(ocel)
    nx.write_gexf(nx_digraph, "converted_graph.gexf")
    os.remove("converted_graph.gexf")


if __name__ == "__main__":
    execute_script()

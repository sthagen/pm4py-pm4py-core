import pm4py
from pm4py.objects.conversion.trie import converter as trie_converter
import pandas
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.trie.obj import Trie


def execute_script():
    log: pandas.DataFrame = pm4py.read_xes("../tests/input_data/running-example.xes")

    prefix_tree: Trie = pm4py.discover_prefix_tree(log)

    net: PetriNet
    im: Marking
    fm: Marking
    net, im, fm = trie_converter.apply(prefix_tree, variant=trie_converter.Variants.TO_PETRI_NET)

    pm4py.view_petri_net(net, im, fm, format="svg")


if __name__ == "__main__":
    execute_script()

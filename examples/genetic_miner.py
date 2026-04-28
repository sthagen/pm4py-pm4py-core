import pm4py
import os
import importlib.util
from examples import examples_conf
from pm4py.algo.discovery.genetic.algorithm import Parameters
import pandas
from pm4py.objects.petri_net.obj import Marking, PetriNet


def execute_script():
    log: pandas.DataFrame = pm4py.read_xes(os.path.join("..", "tests", "input_data", "running-example.xes"))
    net: PetriNet
    im: Marking
    fm: Marking
    net, im, fm = pm4py.discover_petri_net_genetic(log, population_size = 10, generations = 10)

    fitness_tbr: dict[str, float] = pm4py.fitness_token_based_replay(log, net, im, fm)
    print("fitness_tbr", fitness_tbr)
    precision_tbr: float = pm4py.precision_token_based_replay(log, net, im, fm)
    print("precision_tbr", precision_tbr)

    if importlib.util.find_spec("graphviz"):
        pm4py.view_petri_net(net, im, fm, format=examples_conf.TARGET_IMG_FORMAT)


if __name__ == "__main__":
    execute_script()

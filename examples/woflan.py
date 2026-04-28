from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.algo.discovery.alpha import algorithm as alpha_miner
from pm4py.algo.analysis.woflan import algorithm as woflan
import os
from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net.obj import Marking, PetriNet


def execute_script():
    log: EventLog = xes_importer.apply(os.path.join("..", "tests", "input_data", "running-example.xes"))
    net: PetriNet
    im: Marking
    fm: Marking
    net, im, fm = alpha_miner.apply(log)
    is_sound, diagn = woflan.apply(net, im, fm, parameters={"print_diagnostics": True, "return_diagnostics": True})
    print("is_sound", is_sound)
    print(diagn)


if __name__ == "__main__":
    execute_script()

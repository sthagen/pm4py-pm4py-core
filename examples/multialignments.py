import os
from pm4py.algo.conformance.multialignments.variants.discounted_a_star import apply as multii
from pm4py.algo.conformance.multialignments.algorithm import Parameters
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.petri_net.importer import importer as petri_importer
from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net.obj import Marking, PetriNet


def execute_script():
    log_path: str = os.path.join("..", "tests", "input_data", "running-example.xes")
    pnml_path: str = os.path.join("..", "tests", "input_data", "running-example.pnml")
    log: EventLog = xes_importer.apply(log_path)
    net: PetriNet
    marking: Marking
    fmarking: Marking
    net, marking, fmarking = petri_importer.apply(pnml_path)

    THETA: float = 1.1
    MU: int =  20
    multiali = multii(log,net,marking,fmarking, parameters={Parameters.EXPONENT:THETA, Parameters.MARKING_LIMIT:MU})
    print("Multi-alignment:",multiali['multi-alignment'])
    print("Maximal Levenshtein Edit Distance to Log:", multiali['max_distance_to_log'])


if __name__ == '__main__':
    execute_script()

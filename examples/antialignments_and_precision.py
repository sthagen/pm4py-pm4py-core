import os

from pm4py.algo.conformance.antialignments.variants.discounted_a_star import apply as antii
from pm4py.algo.conformance.antialignments.algorithm import Parameters
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.petri_net.importer import importer as petri_importer


def execute_script():
    log_path: "str" = os.path.join("..", "tests", "input_data", "running-example.xes")
    pnml_path: "str" = os.path.join("..", "tests", "input_data", "running-example.pnml")
    log: "EventLog" = xes_importer.apply(log_path)
    net: "PetriNet"
    marking: "Marking"
    fmarking: "Marking"
    net, marking, fmarking = petri_importer.apply(pnml_path)

    THETA: "float" = 1.5
    MU: "int" =  20
    EPSILON: "float" = 0.01
    resAnti = antii(log,net,marking,fmarking, parameters={Parameters.EXPONENT:THETA,
                                                          Parameters.EPSILON:EPSILON,
                                                          Parameters.MARKING_LIMIT:MU})
    print(resAnti['anti-alignment'])
    print("Precision:",resAnti['precision'])


if __name__ == '__main__':
    execute_script()

import os
import time
from pm4py.algo.conformance.alignments.petri_net import algorithm as ali
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.petri_net.importer import importer as petri_importer
from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net.obj import PetriNet, Marking


def synchronous_discounted_alignment():
    '''
    This function runs an alignment based on the discounted edit distance
    By using the synchronous product
    :return:
    '''
    log_path: str = os.path.join("..", "tests", "input_data", "running-example.xes")
    pnml_path: str = os.path.join("..", "tests", "input_data", "running-example.pnml")
    log: EventLog = xes_importer.apply(log_path)
    net: PetriNet
    marking: Marking
    fmarking: Marking
    net, marking, fmarking = petri_importer.apply(pnml_path)

    # to see the net :
    #vizu(net,marking,fmarking).view()

    start: float=time.time()

    alignments1 = ali.apply(log._list[0], net, marking, fmarking,
                            variant=ali.VERSION_DISCOUNTED_A_STAR,
                            parameters={ali.Parameters.SYNCHRONOUS:True,ali.Parameters.EXPONENT:1.1})
    print(alignments1)
    print("Time:",(time.time()-start))

def no_synchronous_discounted_alignment():
    '''
    This function runs an alignment based on the discounted edit distance
    By using the Petri net and petri_net.utils.align_utils.discountedEditDistance function
    '''
    log_path: str = os.path.join("..", "tests", "input_data", "running-example.xes")
    pnml_path: str = os.path.join("..", "tests", "input_data", "running-example.pnml")
    log: EventLog = xes_importer.apply(log_path)
    net: PetriNet
    marking: Marking
    fmarking: Marking
    net, marking, fmarking = petri_importer.apply(pnml_path)

    start: float=time.time()

    alignments1 = ali.apply(log._list[0], net, marking, fmarking,
                            variant=ali.VERSION_DISCOUNTED_A_STAR,
                            parameters={ali.Parameters.SYNCHRONOUS:False,ali.Parameters.EXPONENT:1.1})
    print(alignments1)
    print("Time:",(time.time()-start))


def execute_script():
    synchronous_discounted_alignment()
    no_synchronous_discounted_alignment()


if __name__ == '__main__':
    execute_script()

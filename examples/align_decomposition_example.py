from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.algo.conformance.alignments.decomposed import algorithm as dec_align
from pm4py.algo.evaluation.replay_fitness import algorithm as rep_fit
from pm4py.objects.conversion.process_tree import converter as process_tree_converter
import os
import time
from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.process_tree.obj import ProcessTree


def execute_script():
    # import the a32f0n00 log
    log: EventLog = xes_importer.apply(os.path.join("..", "tests", "compressed_input_data", "09_a32f0n00.xes.gz"))
    # discover a model using the inductive miner
    process_tree: ProcessTree = inductive_miner.apply(log)
    net: PetriNet
    im: Marking
    fm: Marking
    net, im, fm = process_tree_converter.apply(process_tree)
    # apply the alignments decomposition with a maximal number of border disagreements set to 5
    aa: float = time.time()
    aligned_traces = dec_align.apply(log, net, im, fm, parameters={
        dec_align.Variants.RECOMPOS_MAXIMAL.value.Parameters.PARAM_THRESHOLD_BORDER_AGREEMENT: 5})
    bb: float = time.time()
    print(bb-aa)
    # print(aligned_traces)
    # calculate the fitness over the recomposed alignment (use the classical evaluation)
    fitness = rep_fit.evaluate(aligned_traces, variant=rep_fit.Variants.ALIGNMENT_BASED)
    print(fitness)


if __name__ == "__main__":
    execute_script()

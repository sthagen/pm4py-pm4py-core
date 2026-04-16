from pm4py.objects.log.importer.xes import importer
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
import memory_profiler
import time
import os
from pm4py.objects.conversion.process_tree import converter as process_tree_converter


class Shared:
    log: "EventLog" = importer.apply(os.path.join("..", "tests", "input_data", "receipt.xes"))
    process_tree: "ProcessTree" = inductive_miner.apply(log)
    net: "PetriNet"
    im: "Marking"
    fm: "Marking"
    net, im, fm = process_tree_converter.apply(process_tree)


def nothing():
    time.sleep(3)


def f():
    aa: "float" = time.time()
    aligned_traces = alignments.apply(Shared.log, Shared.net, Shared.im, Shared.fm,
                                      variant=alignments.Variants.VERSION_DIJKSTRA_LESS_MEMORY)
    bb: "float" = time.time()
    print(bb - aa)


def g():
    aa: "float" = time.time()
    aligned_traces = alignments.apply(Shared.log, Shared.net, Shared.im, Shared.fm,
                                      variant=alignments.Variants.VERSION_DIJKSTRA_NO_HEURISTICS)
    bb: "float" = time.time()
    print(bb - aa)


if __name__ == "__main__":
    memory_usage = memory_profiler.memory_usage(nothing)
    nothing = max(memory_usage)
    print(nothing)
    memory_usage = memory_profiler.memory_usage(f)
    print(memory_usage)
    print(max(memory_usage) - nothing)
    memory_usage = memory_profiler.memory_usage(g)
    print(memory_usage)
    print(max(memory_usage) - nothing)

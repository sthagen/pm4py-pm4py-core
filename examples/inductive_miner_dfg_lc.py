import pm4py
import os
from collections import Counter
from pm4py.objects.dfg.obj import DFG
from pm4py.algo.discovery.inductive.variants.imd import IMD
from pm4py.algo.discovery.inductive.dtypes.im_dfg import InductiveDFG
from pm4py.algo.discovery.inductive.dtypes.im_ds import IMDataStructureDFG
from pm4py.objects.log.obj import EventLog
from pm4py.objects.process_tree.obj import ProcessTree


def __build_dfg_lc(log, act_key, start_timestamp, complete_timestamp):
    dfg: Counter = Counter()
    start_activities: Counter = Counter()
    end_activities: Counter = Counter()
    for trace in log:
        if trace:
            start_activities[trace[0][act_key]] += 1
            i: int = 0
            max_ct_idx: int = 0
            while i < len(trace):
                ct = trace[i][complete_timestamp]
                if ct > trace[max_ct_idx][complete_timestamp]:
                    max_ct_idx = i
                j: int = i + 1
                while j < len(trace):
                    st = trace[j][start_timestamp]
                    dfg[(trace[i][act_key], trace[j][act_key])] += 1
                    if st >= ct:
                        break
                    else:
                        dfg[(trace[j][act_key], trace[i][act_key])] += 1
                    j = j + 1
                i = i + 1
            end_activities[trace[max_ct_idx][act_key]] += 1

    return DFG(dfg, start_activities, end_activities)


def execute_script():
    log: EventLog = pm4py.read_xes(os.path.join("..", "tests", "input_data", "interval_event_log.xes"), return_legacy_log_object=True)

    process_tree0: ProcessTree = pm4py.discover_process_tree_inductive(log)
    print(process_tree0)

    dfg = __build_dfg_lc(log, "concept:name", "start_timestamp", "time:timestamp")

    imd: IMD = IMD({})
    idfg: InductiveDFG = InductiveDFG(dfg=dfg, skip=False)
    process_tree = imd.apply(IMDataStructureDFG(idfg), {})

    print(process_tree)


if __name__ == "__main__":
    execute_script()

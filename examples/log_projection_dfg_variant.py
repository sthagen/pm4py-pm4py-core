import pm4py
from pm4py.algo.conformance.alignments.dfg.variants import classic as dfg_alignments
from pm4py.algo.conformance.alignments.edit_distance.variants import edit_distance


def execute_script():
    log: "EventLog" = pm4py.read_xes("../tests/input_data/receipt.xes", return_legacy_log_object=True)

    filtered_log: "EventLog | pandas.DataFrame" = pm4py.filter_variants_top_k(log, 1)
    dfg: "dict"
    sa: "dict"
    ea: "dict"
    dfg, sa, ea = pm4py.discover_dfg(filtered_log)
    projected_log: "EventLog" = dfg_alignments.project_log_on_dfg(log, dfg, sa, ea)
    print(projected_log)

    variant = ('Confirmation of receipt', 'T02 Check confirmation of receipt', 'T04 Determine confirmation of receipt',
               'T05 Print and send confirmation of receipt', 'T06 Determine necessity of stop advice',
               'T10 Determine necessity to stop indication')
    projected_log2: "EventLog" = edit_distance.project_log_on_variant(log, variant)
    print(projected_log2)


if __name__ == "__main__":
    execute_script()

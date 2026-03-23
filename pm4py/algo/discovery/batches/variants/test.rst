Discovers an Heuristics Net using Heuristics Miner.

Parameters
----------
dfg
    Directly-Follows Graph
activities
    (If provided) list of activities of the log
activities_occurrences
    (If provided) dictionary of activities occurrences
start_activities
    (If provided) dictionary of start activities occurrences
end_activities
    (If provided) dictionary of end activities occurrences
parameters
    Possible parameters of the algorithm,
    including:

        - Parameters.ACTIVITY_KEY
        - Parameters.TIMESTAMP_KEY
        - Parameters.CASE_ID_KEY
        - Parameters.DEPENDENCY_THRESH
        - Parameters.AND_MEASURE_THRESH
        - Parameters.MIN_ACT_COUNT
        - Parameters.MIN_DFG_OCCURRENCES
        - Parameters.DFG_PRE_CLEANING_NOISE_THRESH
        - Parameters.LOOP_LENGTH_TWO_THRESH

variant
    Variant of the algorithm:

        - Variants.CLASSIC

Returns
------------
net
    Petri net
im
    Initial marking
fm
    Final marking
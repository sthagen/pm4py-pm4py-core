# Directly-Follows Graphs

The directly-follows graphs are one of the simplest classes of process models. The nodes are the activities of the DFG. The edges report the number of times two activities follow each other. In PM4Py, we offer support for advanced operations on top of the directly-follows graphs. In particular, the discovery of the directly-follows graph, along with the start and end activities of the log, can be done using the command:

```python
import pm4py

if __name__ == "__main__":
    dfg, sa, ea = pm4py.discover_directly_follows_graph(log)
```

Instead, the discovery of the activities of the log, along with the number of occurrences, can be done, assuming that `concept:name` is the attribute reporting the activity, using:

```python
import pm4py

if __name__ == "__main__":
    activities_count = pm4py.get_event_attribute_values(log, "concept:name")
```

## Filtering activities/paths

Directly-follows graphs can contain a huge number of activities and paths, with some of them being outliers. In this section, we will see how to filter the activities and paths of the graph, keeping a subset of its behavior. We can load an example log and calculate the directly-follows graph.

```python
import pm4py

if __name__ == "__main__":
    log = pm4py.read_xes("tests/input_data/running-example.xes")
    dfg, sa, ea = pm4py.discover_directly_follows_graph(log)
    activities_count = pm4py.get_event_attribute_values(log, "concept:name")
```

The filtering on the activities percentage is applied as in the following snippet. The most frequent activities according to the percentage are kept, along with all the activities that keep the graph connected. If a percentage of 0% is specified, then the most frequent activity (and the activities keeping the graph connected) is retrieved. Specifying `0.2` as in the example, we want to keep 20% of activities. The filter is applied concurrently to the DFG, to the start activities, to the end activities, and to the dictionary containing the activity occurrences. In this way, consistency is kept.

```python
from pm4py.algo.filtering.dfg import dfg_filtering

if __name__ == "__main__":
    dfg, sa, ea, activities_count = dfg_filtering.filter_dfg_on_activities_percentage(
        dfg, sa, ea, activities_count, 0.2
    )
```

The filtering on the paths percentage is applied as in the following snippet. The most frequent paths according to the percentage are kept, along with all the paths that are necessary to keep the graph connected. If a percentage of 0% is specified, then the most frequent path (and the paths keeping the graph connected) is retrieved. Specifying `0.2` as in the example, we want to keep 20% of paths. The filter is applied concurrently to the DFG, to the start activities, to the end activities, and to the dictionary containing the activity occurrences. In this way, consistency is kept.

```python
from pm4py.algo.filtering.dfg import dfg_filtering

if __name__ == "__main__":
    dfg, sa, ea, activities_count = dfg_filtering.filter_dfg_on_paths_percentage(
        dfg, sa, ea, activities_count, 0.2
    )
```

## Playout of a DFG

A playout operation on a directly-follows graph is useful to retrieve the traces that are allowed from the directly-follows graph. In this case, a trace is a set of activities visited in the DFG from the start node to the end node. We can assign a probability to each trace (assuming that the DFG represents a Markov chain). In particular, we are interested in getting the most likely traces. In this section, we will see how to perform the playout of a directly-follows graph. We can load an example log and calculate the directly-follows graph.

```python
import pm4py

if __name__ == "__main__":
    log = pm4py.read_xes("tests/input_data/running-example.xes")
    dfg, sa, ea = pm4py.discover_directly_follows_graph(log)
    activities_count = pm4py.get_event_attribute_values(log, "concept:name")
```

Then, we can perform the playout operation.

```python
if __name__ == "__main__":
    simulated_log = pm4py.play_out(dfg, sa, ea)
```

## Alignments on a DFG

A popular conformance checking technique is that of alignments. Alignments are usually performed on Petri nets; however, this could take time since the state space of Petri nets can be huge. It is also possible to perform alignments on a directly-follows graph. Since the state space of a directly-follows graph is small, the result is a very efficient computation of alignments. This permits quick diagnostics on the activities and paths that are executed in a wrong way. In this section, we will show an example of how to perform alignments between a process execution and a DFG. We can load an example log and calculate the directly-follows graph.

```python
import pm4py

if __name__ == "__main__":
    log = pm4py.read_xes("tests/input_data/running-example.xes")
    dfg, sa, ea = pm4py.discover_directly_follows_graph(log)
    activities_count = pm4py.get_event_attribute_values(log, "concept:name")
```

Then, we can perform alignments between the process executions of the log and the DFG:

```python
if __name__ == "__main__":
    alignments = pm4py.conformance_diagnostics_alignments(simulated_log, dfg, sa, ea)
```

The output of the alignments is equivalent to the one obtained against Petri nets. In particular, the output is a list containing for each trace the result of the alignment. Each alignment consists of some moves from the start to the end of both the trace and the DFG. We can have sync moves, moves on the log (whether a move in the process execution is not mimicked by the DFG), and moves on the model (whether a move is needed in the model that is not supported by the process execution).

## Convert Directly-Follows Graph to a Workflow Net

The Directly-Follows Graph is the representation of a process provided by many commercial tools. An idea of Sander Leemans is about converting the DFG into a workflow net that perfectly mimics the DFG. This is called DFG mining. The following steps are useful to load the log, calculate the DFG, convert it into a workflow net, and perform alignments. First, we have to import the log. Subsequently, we have to mine the Directly-Follows Graph. This DFG can then be converted to a workflow net.

```python
import pm4py
import os

if __name__ == "__main__":
    log = pm4py.read_xes(os.path.join("tests", "input_data", "running-example.xes"))

    from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
    dfg = dfg_discovery.apply(log)

    from pm4py.objects.conversion.dfg import converter as dfg_mining
    net, im, fm = dfg_mining.apply(dfg)
```

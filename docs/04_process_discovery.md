# Process Discovery

Process Discovery algorithms aim to find a suitable process model that describes the order of events/activities executed during a process execution. Below, we created an overview to visualize the advantages and disadvantages of the mining algorithms.

| Alpha | Alpha+ | Heuristic | Inductive |
|---|---|---|---|
| Cannot handle loops of length one and length two | Can handle loops of length one and length two | Takes frequency into account | Can handle invisible tasks |
| Invisible and duplicated tasks cannot be discovered | Invisible and duplicated tasks cannot be discovered | Detects short loops | Model is sound |
| Discovered model might not be sound | Discovered model might not be sound | Does not guarantee a sound model | Most used process mining algorithm |
| Weak against noise | Weak against noise | | |

## Alpha Miner

The Alpha Miner is one of the most well-known Process Discovery algorithms and is able to find:

- A Petri net model where all the transitions are visible and unique and correspond to classified events (for example, activities).
- An initial marking that describes the status of the Petri net model when an execution starts.
- A final marking that describes the status of the Petri net model when an execution ends.

We provide an example where a log is read, the Alpha algorithm is applied, and the Petri net along with the initial and final markings are found. The log we take as input is the

`running-example.xes`.

First, the log has to be imported.

```python
import os
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests","input_data","running-example.xes"))
```

Subsequently, the Alpha Miner is applied.

```python
if __name__ == "__main__":
	net, initial_marking, final_marking = pm4py.discover_petri_net_alpha(log)
```

## Inductive Miner

In PM4Py, we offer an implementation of the inductive miner (IM), the inductive miner infrequent (IMf), and the inductive miner directly-follows (IMd) algorithms. The papers describing the approaches are the following:

- **Inductive Miner**: Discovering block-structured process models from event logs—a constructive approach ([link](http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.396.197&rep=rep1&type=pdf)),
- **Inductive Miner infrequent**: Discovering block-structured process models from event logs containing infrequent behaviour ([link](http://www.padsweb.rwth-aachen.de/wvdaalst/publications/p761.pdf)),
- **Inductive Miner directly-follows**: Scalable process discovery with guarantees ([link](http://www.processmining.org/_media/blogs/pub2015/bpmds_directly-follows_mining.pdf)).

The basic idea of the Inductive Miner is to detect a 'cut' in the log (e.g., sequential cut, parallel cut, concurrent cut, and loop cut) and then recur on sublogs found by applying the cut until a base case is found. The directly-follows variant avoids the recursion on the sublogs but uses the Directly Follows graph.

Inductive Miner models usually make extensive use of hidden transitions, especially for skipping/looping a portion of the model. Furthermore, each visible transition has a unique label (there are no transitions in the model that share the same label).

Two process models can be derived: Petri Net and Process Tree.

To mine a Petri Net, we provide an example. A log is read, the inductive miner is applied, and the Petri net along with the initial and final markings are found. The log we take as input is the 

`running-example.xes`.

First, the log is read, then the inductive miner algorithm is applied.

```python
import os
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests","input_data","running-example.xes"))
	net, initial_marking, final_marking = pm4py.discover_petri_net_inductive(log)
```

To obtain a process tree, the provided code snippet can be used. The last two lines of code are responsible for the visualization of the process tree.

```python
import pm4py

if __name__ == "__main__":
	tree = pm4py.discover_process_tree_inductive(log)

	pm4py.view_process_tree(tree)
```

It is also possible to convert a process tree into a Petri net.

```python
import pm4py

if __name__ == "__main__":
	net, initial_marking, final_marking = pm4py.convert_to_petri_net(tree)
```

## Heuristic Miner

Heuristics Miner is an algorithm that acts on the directly-follows graph, providing ways to handle noise and to find common constructs (dependencies between two activities, AND). The output of the Heuristics Miner is a Heuristics Net, an object that contains the activities and the relationships between them. The Heuristics Net can then be converted into a Petri net. The paper can be accessed by clicking on the following link: [this link](https://pdfs.semanticscholar.org/1cc3/d62e27365b8d7ed6ce93b41c193d0559d086.pdf).

It is possible to obtain a Heuristic Net and a Petri Net. To apply the Heuristics Miner to discover a Heuristic Net, it is necessary to import a log. Then, a Heuristic Net can be found. There are also numerous possible parameters that can be inspected by clicking on the following button:

Inspect parameters

```python
import pm4py
import os

if __name__ == "__main__":
	log_path = os.path.join("tests", "compressed_input_data", "08_receipt.xes.gz")
	log = pm4py.read_xes(log_path)

	heu_net = pm4py.discover_heuristics_net(log, dependency_threshold=0.99)
```

| Parameter name       | Meaning                                                              |
|----------------------|----------------------------------------------------------------------|
| dependency_threshold | Dependency threshold of the Heuristics Miner (default: 0.5)         |
| and_threshold        | AND measure threshold of the Heuristics Miner (default: 0.65)       |
| loop_two_threshold   | Threshold for loops of length 2 (default: 0.5)                      |

To visualize the Heuristic Net, code is also provided on the right-hand side.

```python
import pm4py

if __name__ == "__main__":
	pm4py.view_heuristics_net(heu_net)
```

To obtain a Petri Net based on the Heuristics Miner, the code on the right-hand side can be used. Also, this Petri Net can be visualized.

```python
import pm4py

if __name__ == "__main__":
	net, im, fm = pm4py.discover_petri_net_heuristics(log, dependency_threshold=0.99)

	pm4py.view_petri_net(net, im, fm)
```

## Directly-Follows Graph

Process models modeled using Petri nets have well-defined semantics: a process execution starts from the places included in the initial marking and finishes at the places included in the final marking. In this section, another class of process models, Directly-Follows Graphs, is introduced. Directly-Follows graphs are graphs where the nodes represent events/activities in the log and directed edges are present between nodes if there is at least one trace in the log where the source event/activity is followed by the target event/activity. On top of these directed edges, it is easy to represent metrics like frequency (counting the number of times the source event/activity is followed by the target event/activity) and performance (some aggregation, for example, the mean, of time elapsed between the two events/activities).

First, we have to import the log. Subsequently, we can extract the Directly-Follows Graph. Additionally, code is provided to visualize the Directly-Follows Graph. This visualization is a colored visualization of the Directly-Follows graph decorated with the frequency of activities.

```python
import os
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests","input_data","running-example.xes"))
	dfg, start_activities, end_activities = pm4py.discover_dfg(log)
	pm4py.view_dfg(dfg, start_activities, end_activities)
```

To get a Directly-Follows graph decorated with the performance between the edges, two parameters of the previous code have to be replaced.

```python
import os
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests","input_data","running-example.xes"))
	performance_dfg, start_activities, end_activities = pm4py.discover_performance_dfg(log)
	pm4py.view_performance_dfg(performance_dfg, start_activities, end_activities)
```

To save the obtained DFG, for instance in the SVG format, code is also provided on the right-hand side.

```python
import os
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests","input_data","running-example.xes"))
	performance_dfg, start_activities, end_activities = pm4py.discover_performance_dfg(log)
	pm4py.save_vis_performance_dfg(performance_dfg, start_activities, end_activities, 'perf_dfg.svg')
```

## Adding Information About Frequency/Performance

Similar to the Directly-Follows graph, it is also possible to decorate the Petri net with frequency or performance information. This is done by using a replay technique on the model and then assigning frequency/performance to the paths. The `variant` parameter of the visualizer specifies which annotation should be used. The values for the `variant` parameter are as follows:

- `pn_visualizer.Variants.WO_DECORATION`: This is the default value and indicates that the Petri net is not decorated.
- `pn_visualizer.Variants.FREQUENCY`: This indicates that the model should be decorated according to frequency information obtained by applying replay.
- `pn_visualizer.Variants.PERFORMANCE`: This indicates that the model should be decorated according to performance (aggregated by mean) information obtained by applying replay.

In the case of frequency and performance decoration, it is required to pass the log as a parameter of the visualization (it needs to be replayed).

The code on the right-hand side can be used to obtain the Petri net mined by the Inductive Miner decorated with frequency information.

```python
from pm4py.visualization.petri_net import visualizer as pn_visualizer

if __name__ == "__main__":
	parameters = {pn_visualizer.Variants.FREQUENCY.value.Parameters.FORMAT: "png"}
	gviz = pn_visualizer.apply(net, initial_marking, final_marking, parameters=parameters, variant=pn_visualizer.Variants.FREQUENCY, log=log)
	pn_visualizer.save(gviz, "inductive_frequency.png")
```

## Correlation Miner

In Process Mining, we are used to having logs containing at least:

- A case identifier,
- An activity,
- A timestamp.

The case identifier associates an event happening in a system to a particular execution of the process. This permits applying algorithms such as process discovery, conformance checking, and others. However, in some systems (for example, data collected from IoT systems), it may be difficult to associate a case identifier. For such logs, performing classic process mining is impossible. Correlation mining arises as a response to the challenge of extracting a process model from such event logs that permit reading useful information contained in the logs without a case identifier, which contains only:

- An activity column,
- A timestamp column.

In this description, we assume there is a total order on events (that means that no events happen at the same timestamp). Situations where a total order is not defined are more complicated.

The Correlation Miner is an approach proposed in:

Pourmirza, Shaya, Remco Dijkman, and Paul Grefen. “Correlation miner: mining business process models and event correlations without case identifiers.” *International Journal of Cooperative Information Systems* 26.02 (2017): 1742002.

It aims to resolve this problem by solving an (integer) linear problem defined on top of:

- **The P/S matrix**: expressing the relationship of order between the activities as recorded in the log.
- **The Duration matrix**: expressing an aggregation of the duration between two activities, obtained by solving an optimization problem.

The solution to this problem provides a set of pairs of activities that are, according to the approach, in a directly-follows relationship, along with the strength of the relationship. This is the “frequency” DFG.

A “performance” DFG can be obtained from the Duration matrix, keeping only the entries that appear in the solution of the problem (i.e., the pairs of activities that appear in the “frequency” DFG).

This can then be visualized (using, for example, the PM4Py DFG visualization).

To have a “realistic” example (for which we know the “real” DFG), we can take an existing log and simply remove the case ID column, trying then to reconstruct the DFG without having that.

Let’s try an example of that. First, we load a CSV file into a Pandas dataframe, keeping only the `concept:name` and `time:timestamp` columns:

```python
import pandas as pd
import pm4py

if __name__ == "__main__":
	df = pd.read_csv(os.path.join("tests", "input_data", "receipt.csv"))
	df = pm4py.format_dataframe(df)
	df = df[["concept:name", "time:timestamp"]]
```

Then, we can apply the Correlation Miner approach:

```python
from pm4py.algo.discovery.correlation_mining import algorithm as correlation_miner

if __name__ == "__main__":
	frequency_dfg, performance_dfg = correlation_miner.apply(df, parameters={"pm4py:param:activity_key": "concept:name",
									"pm4py:param:timestamp_key": "time:timestamp"})
```

To better visualize the DFG, we can retrieve the frequency of activities:

```python
if __name__ == "__main__":
	activities_freq = dict(df["concept:name"].value_counts())
```

And then perform the visualization of the DFG:

```python
from pm4py.visualization.dfg import visualizer as dfg_visualizer

if __name__ == "__main__":
	gviz_freq = dfg_visualizer.apply(frequency_dfg, variant=dfg_visualizer.Variants.FREQUENCY, activities_count=activities_freq, parameters={"format": "svg"})
	gviz_perf = dfg_visualizer.apply(performance_dfg, variant=dfg_visualizer.Variants.PERFORMANCE, activities_count=activities_freq, parameters={"format": "svg"})
	dfg_visualizer.view(gviz_freq)
	dfg_visualizer.view(gviz_perf)
```

Visualizing the DFGs, we can say that the Correlation Miner was able to discover a visualization where the main path is clear.

Different variants of the Correlation Miner are available:

| Variants.CLASSIC       | Calculates the P/S matrix and the duration matrix in the classic way (the entire list of events is used)                                                                      |
|---|---|
| Variants.TRACE_BASED  | Calculates the P/S matrix and the duration matrix on a classic event log, trace-by-trace, and merges the results. The resolution of the linear problem permits obtaining a model that is more understandable than the classic DFG calculated on top of the log. |
| Variants.CLASSIC_SPLIT | Calculates the P/S matrix and the duration matrix on the entire list of events, as in the classic version, but splits that into chunks to speed up the computation. Hence, the generated model is less accurate (compared to the CLASSIC version), but the calculation is faster. The default chunk size is 100,000 events. |

## Temporal Profile

We provide in PM4Py an implementation of the temporal profile model. This has been described in:

Stertz, Florian, Jürgen Mangler, and Stefanie Rinderle-Ma. "Temporal Conformance Checking at Runtime based on Time-infused Process Models." *arXiv preprint arXiv:2008.07262* (2020).

A temporal profile measures, for every pair of activities in the log, the average time and the standard deviation between events with the provided activities. The time is measured between the completion of the first event and the start of the second event. Hence, it is assumed to work with an interval log where the events have two timestamps. The output of the temporal profile discovery is a dictionary where each pair of activities (expressed as a tuple) is associated with a pair of numbers: the first is the average and the second is the average standard deviation.

We provide an example of discovery for the temporal profile. We can load an event log and apply the discovery algorithm.

```python
import pm4py
from pm4py.algo.discovery.temporal_profile import algorithm as temporal_profile_discovery

if __name__ == "__main__":
	log = pm4py.read_xes("tests/input_data/running-example.xes")
	temporal_profile = temporal_profile_discovery.apply(log)
```

Some parameters can be used to customize the execution of the temporal profile:

**See Parameters**

| Parameter Key          | Type   | Default        | Description                             |
|---|---|---|---|
| Parameters.ACTIVITY_KEY         | string | concept:name   | The attribute to use as activity.        |
| Parameters.START_TIMESTAMP_KEY | string | start_timestamp | The attribute to use as start timestamp. |
| Parameters.TIMESTAMP_KEY         | string | time:timestamp | The attribute to use as timestamp.       |
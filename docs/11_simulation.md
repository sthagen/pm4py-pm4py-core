# Simulation

In PM4Py, we offer different simulation algorithms that, starting from a model, can produce outputs that follow the model and the various rules provided by the user.

## Playout of a Petri Net

A playout of a Petri net takes as input a Petri net along with an initial marking and returns a list of process executions that are allowed by the process model. We offer different types of playouts:

|Variants.BASIC_PLAYOUT|A basic playout that accepts a Petri net along with an initial marking and returns a specified number of process executions (repetitions may be possible).|
|---|---|
|Variants.EXTENSIVE|A playout that accepts a Petri net along with an initial marking and returns all the executions possible according to the model, up to a provided trace length (may be computationally expensive).|

The list of parameters for such variants are:

Inspect parameters

|Variants.BASIC_PLAYOUT|Parameters.ACTIVITY_KEY|The name of the attribute to use as activity in the playout log.|
|---|---|---|
||Parameters.TIMESTAMP_KEY|The name of the attribute to use as timestamp in the playout log.|
||Parameters.CASE_ID_KEY|The trace attribute that should be used as case identifier in the playout log.|
||Parameters.NO_TRACES|The number of traces that the playout log should contain.|
||Parameters.MAX_TRACE_LENGTH|The maximum trace length (after which the playout of the trace is stopped).|
|Variants.EXTENSIVE|Parameters.ACTIVITY_KEY|The name of the attribute to use as activity in the playout log.|
||Parameters.TIMESTAMP_KEY|The name of the attribute to use as timestamp in the playout log.|
||Parameters.CASE_ID_KEY|The trace attribute that should be used as case identifier in the playout log.|
||Parameters.MAX_TRACE_LENGTH|The maximum trace length (after which the extensive playout is stopped).|

An example application of the basic playout, given a Petri net, to get a log of 50 traces is the following:

```python
from pm4py.algo.simulation.playout.petri_net import algorithm as simulator

if __name__ == "__main__":
    simulated_log = simulator.apply(net, im, variant=simulator.Variants.BASIC_PLAYOUT, parameters={simulator.Variants.BASIC_PLAYOUT.value.Parameters.NO_TRACES: 50})
```

An example application of the extensive playout, given a Petri net, to get the log containing all executions of length ≤ 7:

```python
from pm4py.algo.simulation.playout.petri_net import algorithm as simulator

if __name__ == "__main__":
    simulated_log = simulator.apply(net, im, variant=simulator.Variants.EXTENSIVE, parameters={simulator.Variants.EXTENSIVE.value.Parameters.MAX_TRACE_LENGTH: 7})
```

## Monte Carlo Simulation

A time-related simulation allows determining how probable it is that a process execution is terminated after a given amount of time. This leads to a better estimation of Service Level Agreements or a better identification of the process instances that are most likely to have a high throughput time.

All this starts from a performance DFG, for example, the one discovered from the running-example log

```python
import os
import pm4py

if __name__ == "__main__":
    log = pm4py.read_xes(os.path.join("tests", "input_data", "running-example.xes"))
    log = pm4py.convert_to_event_log(log)
    dfg_perf, sa, ea = pm4py.discover_performance_dfg(log)
```

and the knowledge of the case arrival ratio. The case arrival ratio is the amount of time that passes (on average or median) between the arrival of two consecutive cases. It can be provided by the user or inferred from the event log. The inference from the event log is done by using the following command:

```python
import pm4py

if __name__ == "__main__":
    ratio = pm4py.get_rework_cases_per_activity(log)
    print(ratio)
```

Using the DFG mining approach, it is possible to retrieve a Petri net model from the DFG. This kind of model is the “default” one for Monte Carlo simulation because its execution semantics are very clear. Moreover, the Petri net extracted by the DFG mining approach is a sound workflow net, which provides other good properties to the model.

The DFG mining approach can be applied in the following way:

```python
import pm4py

if __name__ == "__main__":
    net, im, fm = pm4py.convert_to_petri_net(dfg_perf, sa, ea)
```

To perform a basic Monte Carlo simulation, the following code can be used. The following is a sort of resource-constrained simulation, where it is assumed that a place can hold at most 1 token per time. Later, we will see how to provide a higher number of tokens that can be hosted by a place.

```python
from pm4py.algo.simulation.montecarlo import algorithm as montecarlo_simulation
from pm4py.algo.conformance.tokenreplay.algorithm import Variants

if __name__ == "__main__":
    parameters = {}
    parameters[
        montecarlo_simulation.Variants.PETRI_SEMAPH_FIFO.value.Parameters.TOKEN_REPLAY_VARIANT
    ] = Variants.BACKWARDS
    parameters[
        montecarlo_simulation.Variants.PETRI_SEMAPH_FIFO.value.Parameters.PARAM_CASE_ARRIVAL_RATIO
    ] = 10800
    simulated_log, res = montecarlo_simulation.apply(log, net, im, fm, parameters=parameters)
```

During the replay operation, some debug messages are written to the screen. The main outputs of the simulation process are:

|simulated_log|The traces that have been simulated during the simulation.|
|---|---|
|res|The result of the simulation (Python dictionary).|

Among `res`, which is the result of the simulation, we have the following keys:

Inspect outputs

|places_interval_trees|An interval tree for each place that hosts an interval for each time when it was “full” according to the specified maximum number of tokens per place.|
|---|---|
|transitions_interval_trees|An interval tree for each transition that contains all the time intervals in which the transition was enabled but not yet fired (i.e., the time between a transition being fully enabled and the consumption of tokens from the input places).|
|cases_ex_time|A list containing the throughput times for all the cases of the log.|
|median_cases_ex_time|The median throughput time of the cases in the simulated log.|
|input_case_arrival_ratio|The case arrival ratio that was provided by the user or automatically calculated from the event log.|
|total_cases_time|The difference between the last timestamp of the log and the first timestamp of the simulated log.|

The last four items of the previous list are simple Python objects (floats and lists, specifically). The interval trees objects can be used in the following way to get time-specific information. For example, the following code snippet prints, for a random transition in the model, the number of intervals that are overlapping for 11 different points (including the minimum and maximum timestamp in the log) that are uniformly distributed across the time interval of the log.

```python
import random
if __name__ == "__main__":
    last_timestamp = max(event["time:timestamp"] for trace in log for event in trace).timestamp()
    first_timestamp = min(event["time:timestamp"] for trace in log for event in trace).timestamp()
    pick_trans = random.choice(list(res["transitions_interval_trees"]))
    print(pick_trans)
    n_div = 10
    i = 0
    while i < n_div:
        timestamp = first_timestamp + (last_timestamp - first_timestamp)/n_div * i
        print("\t", timestamp, len(res["transitions_interval_trees"][pick_trans][timestamp]))
        i = i + 1
```

The following code snippet instead prints, for a random transition in the model, the number of intervals that are overlapping for 11 different points (including the minimum and maximum timestamp of the log) that are uniformly distributed across the time interval of the log:

```python
import random
if __name__ == "__main__":
    last_timestamp = max(event["time:timestamp"] for trace in log for event in trace).timestamp()
    first_timestamp = min(event["time:timestamp"] for trace in log for event in trace).timestamp()
    pick_place = random.choice(list(res["places_interval_trees"]))
    print(pick_place)
    n_div = 10
    i = 0
    while i < n_div:
        timestamp = first_timestamp + (last_timestamp - first_timestamp)/n_div * i
        print("\t", timestamp, len(res["places_interval_trees"][pick_place][timestamp]))
        i = i + 1
```

The information can be used to build some graphs using external programs such as Microsoft Excel.

The simulation process can be summarized as follows:

- An event log and a model (DFG) are considered.
- Internally in the simulation, a replay operation is done between the log and the model.
- The replay operation leads to the construction of a stochastic map that associates each transition with a probability distribution (for example, a normal distribution, an exponential distribution, etc.). The probability distribution that maximizes the likelihood of the observed values during the replay is chosen. The user can force a specific distribution (like exponential) if desired.
- Moreover, during the replay operation, the frequency of each transition is determined. This helps in selecting, in a “weighted” way, one of the transitions enabled in a marking when the simulation occurs.
- The simulation process occurs. For each one of the traces that are generated (the distance between their start is fixed), a thread is spawned, and stochastic choices are made. The ability to use a given place (depending on the maximum number of resources that can be used) is governed by a semaphore object in Python.
- A maximum amount of time is specified for the simulation. If one or more threads exceed that amount of time, the threads are killed, and the corresponding trace is not added to the simulation log.

Hence, several parameters are important in order to perform a Monte Carlo simulation. These parameters, which are inside the `petri_semaph_fifo` class, are (ordered by importance).

Inspect parameters

|Variants.PETRI_SEMAPH_FIFO|Parameters.PARAM_NUM_SIMULATIONS|Number of simulations performed (the goal is to have that number of traces in the model).|
|---|---|---|
||Parameters.PARAM_CASE_ARRIVAL_RATIO|The case arrival ratio specified by the user.|
||Parameters.PARAM_MAP_RESOURCES_PER_PLACE|A map containing, for each place of the Petri net, the maximum number of tokens.|
||Parameters.PARAM_DEFAULT_NUM_RESOURCES_PER_PLACE|If the map of resources per place is not specified, use the specified maximum number of resources per place.|
||Parameters.PARAM_MAX_THREAD_EXECUTION_TIME|Specifies the maximum execution time of the simulation (for example, 60 seconds).|
||Parameters.PARAM_SMALL_SCALE_FACTOR|Specifies the ratio between the “real” time scale and the simulation time scale. A higher ratio means that the simulation runs faster but is generally less accurate. A lower ratio means that the simulation runs slower and is generally more accurate (in providing detailed diagnostics). The default choice is 864000 seconds (10 days). This means that one second in the simulation corresponds to 10 days of real time.|
||Parameters.PARAM_ENABLE_DIAGNOSTICS|Enables the printing of simulation diagnostics through Python's “logging” class.|
||Parameters.ACTIVITY_KEY|The attribute of the log to use as activity.|
||Parameters.TIMESTAMP_KEY|The attribute of the log to use as timestamp.|
||Parameters.TOKEN_REPLAY_VARIANT|The variant of the token-based replay to use: `token_replay`, the classic variant that cannot handle duplicate transitions; `backwards`, the backwards token-based replay that is slower but can handle invisible transitions.|
||Parameters.PARAM_FORCE_DISTRIBUTION|If specified, the distribution that is forced for the transitions (normal, exponential).|
||Parameters.PARAM_DIAGN_INTERVAL|The time interval at which diagnostics should be printed (for example, diagnostics printed every 10 seconds).|

## Extensive Playout of a Process Tree

An extensive playout operation allows obtaining (up to the provided limits) the entire language of the process model. Performing an extensive playout operation on a Petri net can be incredibly expensive (the reachability graph needs to be explored). Process trees, with their bottom-up structure, allow obtaining the entire language of an event log much more easily, starting from the language of the leaves (which is obvious) and then following specific merge rules for the operators.

However, since the language of a process tree can be incredibly vast (when parallel operators are involved) or even infinite (when loops are involved), extensive playouts are possible only up to some limits:

- A specification of the maximum number of occurrences for a loop must be made if a loop is present. This stops an extensive playout operation at the given number of occurrences.
- Since the number of different executions, when loops are involved, is still incredibly large, it is possible to specify the maximum length of a trace to be returned. Traces that exceed the maximum length are automatically discarded.
- To further limit the number of different executions, the maximum number of traces returned by the algorithm might be specified.

Moreover, from the structure of the process tree, it is easy to infer the minimum length of a trace allowed by the process model (always following the bottom-up approach).

Some reasonable settings for the extensive playout are:

- Overall, the maximum number of traces returned by the algorithm is set to 100,000.
- The maximum length of a trace output by the playout is, by default, set to the minimum length of a trace accepted by a process tree.
- The maximum number of loops is set to the minimum length of a trace divided by two.

The list of parameters are:

Inspect parameters

|MAX_LIMIT_NUM_TRACES|Maximum number of traces returned by the algorithm.|
|---|---|
|MAX_TRACE_LENGTH|Maximum length of a trace output by the algorithm.|
|MAX_LOOP_OCC|Maximum number of times a loop can be entered.|

In the following, we see how the playout can be executed. First, a log can be imported:

```python
import pm4py
import os

if __name__ == "__main__":
    log = pm4py.read_xes(os.path.join("tests", "input_data", "receipt.xes"))
```

Then, a process tree can be discovered using the inductive miner algorithm.

```python
if __name__ == "__main__":
    tree = pm4py.discover_process_tree_inductive(log)
```

We specify retrieving traces of length at most 3 and that we want to retrieve at most 100,000 traces.

```python
from pm4py.algo.simulation.playout.process_tree import algorithm as tree_playout

if __name__ == "__main__":
    playout_variant = tree_playout.Variants.EXTENSIVE
    param = tree_playout.Variants.EXTENSIVE.value.Parameters

    simulated_log = tree_playout.apply(
        tree,
        variant=playout_variant,
        parameters={
            param.MAX_TRACE_LENGTH: 3,
            param.MAX_LIMIT_NUM_TRACES: 100000
        }
    )
    print(len(simulated_log))
```

At this point, the extensive playout operation is complete.

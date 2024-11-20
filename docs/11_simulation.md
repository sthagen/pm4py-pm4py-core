

# Simulation


In pm4py, we offer different simulation algorithms, that starting from a model,
are able to produce an output that follows the model and the different rules that have
been provided by the user.


## Playout of a Petri Net


A playout of a Petri net takes as input a Petri net along with an initial marking,
and returns a list of process executions that are allowed from the process model.
We offer different types of playouts:


|Variants.BASIC_PLAYOUT|A basic playout that accepts a Petri net along with an initial marking, and returns a specified number of process executions (repetitions may be possible).|
|---|---|
|Variants.EXTENSIVE|A playout that accepts a Petri net along with an initial marking, and returns all the executions that are possible according to the model, up to a provided length of trace (may be computationally expensive).|



The list of parameters for such variants are:

Inspect parameters



|Variants.BASIC_PLAYOUT|Parameters.ACTIVITY_KEY|The name of the attribute to use as activity in the playout log.|
|---|---|---|
||Parameters.TIMESTAMP_KEY|The name of the attribute to use as timestamp in the playout log.|
||Parameters.CASE_ID_KEY|The trace attribute that should be used as case identifier in the playout log.|
||Parameters.NO_TRACES|The number of traces that the playout log should contain.|
||Parameters.MAX_TRACE_LENGTH|The maximum trace length (after which, the playout of the trace is stopped).|
|Variants.EXTENSIVE|Parameters.ACTIVITY_KEY|The name of the attribute to use as activity in the playout log.|
||Parameters.TIMESTAMP_KEY|The name of the attribute to use as timestamp in the playout log.|
||Parameters.CASE_ID_KEY|The trace attribute that should be used as case identifier in the playout log.|
||Parameters.MAX_TRACE_LENGTH|The maximum trace length (after which, the extensive playout is stopped).|



An example application of the basic playout, given a Petri net, to get a log of 50 traces,
is the following:



```python
from pm4py.algo.simulation.playout.petri_net import algorithm as simulator

if __name__ == "__main__":
	simulated_log = simulator.apply(net, im, variant=simulator.Variants.BASIC_PLAYOUT, parameters={simulator.Variants.BASIC_PLAYOUT.value.Parameters.NO_TRACES: 50})
```


An example application of the extensive playout, given a Petri net, to get the log
containing all the executions of length <= 7:



```python
from pm4py.algo.simulation.playout.petri_net import algorithm as simulator

if __name__ == "__main__":
	simulated_log = simulator.apply(net, im, variant=simulator.Variants.EXTENSIVE, parameters={simulator.Variants.EXTENSIVE.value.Parameters.MAX_TRACE_LENGTH: 7})
```




## Monte Carlo Simulation


A time-related simulation permits to know how probable is that a process execution is terminated
after a given amount of time. This leads to a better estimation of Service Level Agreements, or a
better identification of the process instances that are most likely to have an high throughput time.

All this starts from a performance DFG, for example the one discovered from the
running-example log



```python
import os
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "running-example.xes"))
	log = pm4py.convert_to_event_log(log)
	dfg_perf, sa, ea = pm4py.discover_performance_dfg(log)
```


and the knowledge of the case arrival ratio. The case arrival ratio is the amount of time
that passes (in average, or median) between the arrival of two consecutive cases. It can be
provided by the user or inferred from the event log. The inference from the event log is
done by using the following command:



```python
import pm4py

if __name__ == "__main__":
	ratio = pm4py.get_rework_cases_per_activity(log)
	print(ratio)
```


Using the DFG mining approach, it is possible to retrieve a Petri net model from the DFG. This
kind of models is the “default” one for Monte Carlo simulation (because its execution semantics
is very clear). Moreover, the Petri net extracted by the DFG mining approach is a sound workflow
net (that gives other good properties to the model).
The DFG mining approach can be applied in the following way:



```python
import pm4py

if __name__ == "__main__":
	net, im, fm = pm4py.convert_to_petri_net(dfg_perf, sa, ea)
```


To perform a basic Montecarlo simulation, the following code can be used. The following is a
sort of resource-constrained simulation, where it is assumed that a place can hold at most 1
token per time. Later, we will see how to provide an higher number of tokens that can be
hosted by a place.



```python
from pm4py.algo.simulation.montecarlo import algorithm as montecarlo_simulation
from pm4py.algo.conformance.tokenreplay.algorithm import Variants

if __name__ == "__main__":
	parameters = {}
	parameters[
		montecarlo_simulation.Variants.PETRI_SEMAPH_FIFO.value.Parameters.TOKEN_REPLAY_VARIANT] = Variants.BACKWARDS
	parameters[montecarlo_simulation.Variants.PETRI_SEMAPH_FIFO.value.Parameters.PARAM_CASE_ARRIVAL_RATIO] = 10800
	simulated_log, res = montecarlo_simulation.apply(log, net, im, fm, parameters=parameters)
```


During the replay operation, some debug messages are written to the screen. The main outputs of
the simulation process are:


|simulated_log|The traces that have been simulated during the simulation.|
|---|---|
|res|The result of the simulation (Python dictionary).|



Among 
res
, that is the result of the simulation, we have the following keys:

Inspect outputs



|places_interval_trees|an interval tree for each place, that hosts an interval for each time when it was “full” according to the specified maximum amount of tokens per place.|
|---|---|
|transitions_interval_trees|an interval tree for each transition, that contains all the time intervals in which the transition was enabled but not yet fired (so, the time between a transition was fully enabled and the consumption of the tokens from the input places)|
|cases_ex_time|a list containing the throughput times for all the cases of the log|
|median_cases_ex_time|the median throughput time of the cases in the simulated log|
|input_case_arrival_ratio|the case arrival ratio that was provided by the user, or automatically calculated from the event log.|
|total_cases_time|the difference between the last timestamp of the log, and the first timestamp of the simulated log.|



The last four items of the previous list are simple Python objects (floats and lists in the
specific). The interval trees objects can be used in the following way to get time-specific
information. For example, the following code snippet
prints for a random transition in the model, the number of intervals that are overlapping
for 11 different points (including the minimum and the maximum timestamp in the log) that
are uniformly distributed across the time interval of the log.



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


The following code snippet instead prints, for a random transition in the model, the number
of intervals that are overlapping for 11 different points (including the minimum and the
maximum timestamp of the log) that are uniformly distributed across the time interval of the
log:



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


The information can be used to build some graphs like these (using external programs such as
Microsoft Excel).
The simulation process can be resumed as follows:,

- An event log and a model (DFG) is considered.,

- Internally in the simulation, a replay operation is done between the log and the model.,

- The replay operation leads to the construction of a stochastic map that associates to each
transition a probability distribution (for example, a normal distribution, an exponential
distribution …). The probability distribution that maximizes the likelihood of the observed
values during the replay is chosen. The user can force a specific transition (like
exponential) if he wants.,

- Moreover, during the replay operation, the frequency of each transition is found. That helps
in picking in a “weighted” way one of the transitions enabled in a marking, when the
simulation occurs.,

- The simulation process occurs. For each one of the trace that are generated (the distance
between the start of them is fixed) a thread is spawned, stochastic choices are made. The
possibility to use a given place (depending on the maximum number of resources that is
possible to use) is given by a semaphore object in Python.,

- A maximum amount of time is specified for the simulation. If one or more threads exceed that
amount of time, the threads are killed and the corresponding trace is not added to the
simulation log.
Hence, several parameters are important in order to perform a Monte Carlo simulation. These
parameters, that are inside the 
petri_semaph_fifo
 class, are (ordered by importance).

Inspect parameters



|Variants.PETRI_SEMAPH_FIFO|Parameters.PARAM_NUM_SIMULATIONS|Number of simulations that are performed (the goal is to have such number of traces in the model)|
|---|---|---|
||Parameters.PARAM_CASE_ARRIVAL_RATIO|The case arrival ratio that is specified by the user.|
||Parameters.PARAM_MAP_RESOURCES_PER_PLACE|A map containing for each place of the Petri net the maximum amount of tokens|
||Parameters.PARAM_DEFAULT_NUM_RESOURCES_PER_PLACE|If the map of resources per place is not specified, then use the specified maximum number of resources per place.|
||Parameters.PARAM_MAX_THREAD_EXECUTION_TIME|Specifies the maximum execution time of the simulation (for example, 60 seconds).|
||Parameters.PARAM_SMALL_SCALE_FACTOR|Specifies the ratio between the “real” time scale and the simulation time scale. A higher ratio means that the simulation goes faster but is in general less accurate. A lower ratio means that the simulation goes slower and is in general more accurate (in providing detailed diagnostics). The default choice is 864000 seconds (10 days). So that means that a second in the simulation is corresponding to 10 days of real log.|
||Parameters.PARAM_ENABLE_DIAGNOSTICS|Enables the printing of the simulation diagnostics through the usage of the “logging” class of Python|
||Parameters.ACTIVITY_KEY|The attribute of the log that should be used as activity|
||Parameters.TIMESTAMP_KEY|The attribute of the log that should be used as timestamp|
||Parameters.TOKEN_REPLAY_VARIANT|The variant of the token-based replay to use: token_replay, the classic variant, that cannot handle duplicate transitions; backwards, the backwards token-based replay, that is slower but can handle invisible transitions.|
||Parameters.PARAM_FORCE_DISTRIBUTION|If specified, the distribution that is forced for the transitions (normal, exponential)|
||Parameters.PARAM_DIAGN_INTERVAL|The time interval in which diagnostics should be printed (for example, diagnostics should be printed every 10 seconds).|





## Extensive Playout of a Process Tree


An extensive playout operation permits to obtain (up to the provided limits) the entire language
of the process model. Doing an extensive playout operation on a Petri net can be incredibly
expensive (the reachability graph needs to be explored). Process trees, with their bottom-up
structure, permit to obtain the entire language of an event log in a much easier way, starting
from the language of the leafs (that is obvious) and then following specific merge rules for the
operators.
However, since the language of a process tree can be incredibly vast (when parallel operators are
involved) or also infinite (when loops are involved), the extensive playouts is possible up to
some limits:,

- A specification of the maximum number of occurrences for a loop must be done, if a loop is
there. This stops an extensive playout operation at the given number of occurences.,

- Since the number of different executions, when loops are involved, is still incredibly big,
it is possible to specify the maximum length of a trace to be returned. So, traces that are
above the maximum length are automatically discarded.,

- For further limiting the number of different executions, the maximum number of traces
returned by the algorithm might be provided.
Moreover, from the structure of the process tree, it is easy to infer the minimum length of a
trace allowed by the process model (always following the bottom-up approach).
Some reasonable settings for the extensive playout are the following:,

- Overall, the maximum number of traces returned by the algorithm is set to 100000.,

- The maximum length of a trace that is an output of the playout is, by default, set to the
minimum length of a trace accepted by a process tree.,

- The maximum number of loops is set to be the minimum length of a trace divided by two.
The list of parameters are:

Inspect parameters



|MAX_LIMIT_NUM_TRACES|Maximum number of traces that are returned by the algorithm.|
|---|---|
|MAX_TRACE_LENGTH|Maximum length of a trace that is output of the algorithm.|
|MAX_LOOP_OCC|Maximum number of times we enter in a loop.|



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


We specify to retrieve traces of length at most equal to 3, and we want to retrieve at most
100000 traces.



```python
from pm4py.algo.simulation.playout.process_tree import algorithm as tree_playout

if __name__ == "__main__":
	playout_variant = tree_playout.Variants.EXTENSIVE
	param = tree_playout.Variants.EXTENSIVE.value.Parameters

	simulated_log = tree_playout.apply(tree, variant=playout_variant,
									   parameters={param.MAX_TRACE_LENGTH: 3, param.MAX_LIMIT_NUM_TRACES: 100000})
	print(len(simulated_log))
```


At this point, the extensive playout operation is done.
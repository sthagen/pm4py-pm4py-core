# Statistics

In PM4Py, it is possible to calculate different statistics on classic event logs and dataframes.

## Throughput Time

Given an event log, it is possible to retrieve the list of all the durations of the cases (expressed in seconds).

The only parameter that is needed is the timestamp. The code on the right can be used.

```python
import pm4py
if __name__ == "__main__":
	all_case_durations = pm4py.get_all_case_durations(log)
```

## Case Arrival/Dispersion Ratio

Given an event log, it is possible to retrieve the case arrival ratio, which is the average distance between the arrival of two consecutive cases in the log.

```python
import pm4py
if __name__ == "__main__":
	case_arrival_ratio = pm4py.get_case_arrival_average(log)
```

It is also possible to calculate the case dispersion ratio, which is the average distance between the finishing of two consecutive cases in the log.

```python
from pm4py.statistics.traces.generic.log import case_arrival
if __name__ == "__main__":
	case_dispersion_ratio = case_arrival.get_case_dispersion_avg(log, parameters={
		case_arrival.Parameters.TIMESTAMP_KEY: "time:timestamp"})
```

## Performance Spectrum

The performance spectrum is a novel visualization of the performance of the process based on the time elapsed between different activities in the process executions. The performance spectrum was initially described in:

Denisov, Vadim, et al. "The Performance Spectrum Miner: Visual Analytics for Fine-Grained Performance Analysis of Processes." BPM (Dissertation/Demos/Industry). 2018.

The performance spectrum works with an event log and a list of activities that are considered to build the spectrum. In the following example, the performance spectrum is built on the receipt event log, including the "Confirmation of receipt", "T04 Determine confirmation of receipt", and "T10 Determine necessity to stop indication" activities. The event log is loaded, and the performance spectrum (containing the timestamps at which the different activities happened inside the process execution) is computed and visualized:

```python
import pm4py
import os

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "receipt.xes"))
	log = pm4py.convert_to_event_log(log)
	pm4py.view_performance_spectrum(log, ["Confirmation of receipt", "T04 Determine confirmation of receipt",
										 "T10 Determine necessity to stop indication"], format="svg")
```

In the aforementioned example, we see three horizontal lines corresponding to the activities included in the spectrum and many oblique lines that represent the elapsed times between two activities. The more oblique lines are highlighted with different colors. This allows identifying the timestamps during which the execution was more bottlenecked and possible patterns (FIFO, LIFO).

## Cycle Time and Waiting Time

Two important KPIs for process executions are:

- The Lead Time: the overall time in which the instance was worked, from the start to the end, without considering if it was actively worked or not.

- The Cycle Time: the overall time in which the instance was worked, from the start to the end, considering only the times when it was actively worked.

Within ‘interval’ event logs (those that have a start and an end timestamp), it is possible to calculate incrementally the lead time and the cycle time (event per event). The lead time and the cycle time reported on the last event of the case are those related to the process execution. This makes it easy to understand which activities of the process have caused bottlenecks (e.g., the lead time increases significantly more than the cycle time). The algorithm implemented in PM4Py starts by sorting each case by the start timestamp (so activities started earlier are reported earlier in the log), and it can calculate the lead and cycle time in all situations, including complex ones as shown in the following picture:

In the following, we aim to insert the following attributes to events inside a log:

### Attributes

|@@approx_bh_partial_cycle_time|Incremental cycle time associated with the event (the cycle time of the last event is the cycle time of the instance)|
|---|---|
|@@approx_bh_partial_lead_time|Incremental lead time associated with the event|
|@@approx_bh_overall_wasted_time|Difference between the partial lead time and the partial cycle time values|
|@@approx_bh_this_wasted_time|Wasted time only with regards to the activity described by the ‘interval’ event|
|@@approx_bh_ratio_cycle_lead_time|Measures the incremental Flow Rate (between 0 and 1).|

The method that calculates lead and cycle time can be applied with the following line of code:

```python
from pm4py.objects.log.util import interval_lifecycle
if __name__ == "__main__":
	enriched_log = interval_lifecycle.assign_lead_cycle_time(log)
```

With this, an enriched log that contains for each event the corresponding attributes for lead/cycle time is obtained.

## Sojourn Time

This statistic works only with interval event logs, i.e., event logs where each event has a start timestamp and a completion timestamp.

The average sojourn time statistic allows knowing, for each activity, how much time was spent executing the activity. This is calculated as the average of the time elapsed between the start timestamp and the completion timestamp for the activity's events. We provide an example. First, we import an interval event log.

```python
import pm4py
import os

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "interval_event_log.xes"))
```

Then, we calculate the statistic, which requires providing the attribute that is the start timestamp and the attribute that is the completion timestamp.

```python
from pm4py.statistics.sojourn_time.log import get as soj_time_get

if __name__ == "__main__":
	soj_time = soj_time_get.apply(log, parameters={soj_time_get.Parameters.TIMESTAMP_KEY: "time:timestamp", soj_time_get.Parameters.START_TIMESTAMP_KEY: "start_timestamp"})
	print(soj_time)
```

The same statistic can be applied seamlessly on Pandas dataframes. We provide an alternative class for doing so:

pm4py.statistics.sojourn_time.pandas.get

## Concurrent Activities

This statistic works only with interval event logs, i.e., event logs where each event has a start timestamp and a completion timestamp.

In an interval event log, the definition of an order between events is weaker. Different intersections between a pair of events in a case can happen:

- An event where the start timestamp is greater than or equal to the completion timestamp of the other.

- An event where the start timestamp is greater than or equal to the start timestamp of the other event, but is less than the completion timestamp of the other event.

In particular, the latter case defines event-based concurrency, where several events are actively executed at the same time.

We might be interested in retrieving the set of activities for which such concurrent execution occurs and the frequency of such occurrences. We offer this type of calculation in PM4Py. We provide an example. First, we import an interval event log.

```python
import pm4py
import os

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "interval_event_log.xes"))
```

Then, we calculate the statistic, which requires providing the attribute that is the start timestamp and the attribute that is the completion timestamp.

```python
from pm4py.statistics.concurrent_activities.log import get as conc_act_get

if __name__ == "__main__":
	conc_act = conc_act_get.apply(log, parameters={conc_act_get.Parameters.TIMESTAMP_KEY: "time:timestamp", conc_act_get.Parameters.START_TIMESTAMP_KEY: "start_timestamp"})
	print(conc_act)
```

The same statistic can be applied seamlessly on Pandas dataframes. We provide an alternative class for doing so:

pm4py.statistics.concurrent_activities.pandas.get

## Eventually-Follows Graph

We provide an approach for calculating the eventually-follows graph.

The eventually-follows graph (EFG) is a graph that represents the partial order of the events within the process executions of the log.

Our implementation can be applied to both lifecycle logs (logs where each event has only one timestamp) and to interval logs (where each event has a start and a completion timestamp). In the latter, the start timestamp is actively considered for the definition of the EFG/partial order.

In particular, the method assumes working with lifecycle logs when a start timestamp is NOT passed in the parameters, while it assumes working with interval logs when a start timestamp is passed in the parameters.

We provide an example. First, we import an interval event log.

```python
import pm4py
import os

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "interval_event_log.xes"))
```

Then, we calculate the statistic, which requires providing the attribute that is the completion timestamp and possibly the attribute that is the start timestamp.

```python
import pm4py

if __name__ == "__main__":
	efg_graph = pm4py.discover_eventually_follows_graph(log)
```

## Displaying Graphs

Graphs allow understanding several aspects of the current log (for example, the distribution of a numeric attribute, the distribution of case duration, or events over time).

### Distribution of Case Duration

In the following example, the distribution of case duration is shown in two different graphs: a simple plot and a semi-logarithmic plot (on the X-axis). The semi-logarithmic plot is less sensitive to possible outliers.

First, the receipt log is loaded. Then, the distribution related to case duration is obtained. We can obtain the simple plot or the semi-logarithmic (on the X-axis) plot.

```python
import os
import pm4py

if __name__ == "__main__":
	log_path = os.path.join("tests","input_data","receipt.xes")
	log = pm4py.read_xes(log_path)

	from pm4py.util import constants
	from pm4py.statistics.traces.generic.log import case_statistics
	x, y = case_statistics.get_kde_caseduration(log, parameters={constants.PARAMETER_CONSTANT_TIMESTAMP_KEY: "time:timestamp"})

	from pm4py.visualization.graphs import visualizer as graphs_visualizer

	gviz = graphs_visualizer.apply_plot(x, y, variant=graphs_visualizer.Variants.CASES)
	graphs_visualizer.view(gviz)

	gviz = graphs_visualizer.apply_semilogx(x, y, variant=graphs_visualizer.Variants.CASES)
	graphs_visualizer.view(gviz)
```

### Distribution of Events over Time

In the following example, a graph representing the distribution of events over time is obtained. This is particularly important because it helps to understand in which time intervals the greatest number of events is recorded.

The distribution related to events over time is obtained. The graph can be plotted.

```python
from pm4py.algo.filtering.log.attributes import attributes_filter

if __name__ == "__main__":
	x, y = attributes_filter.get_kde_date_attribute(log, attribute="time:timestamp")

	from pm4py.visualization.graphs import visualizer as graphs_visualizer

	gviz = graphs_visualizer.apply_plot(x, y, variant=graphs_visualizer.Variants.DATES)
	graphs_visualizer.view(gviz)
```

### Distribution of a Numeric Attribute

In the following example, two graphs related to the distribution of a numeric attribute are obtained: a normal plot and a semilogarithmic plot (on the X-axis), which is less sensitive to outliers.

First, a filtered version of the Road Traffic log is loaded. Then, the distribution of the numeric attribute 'amount' is obtained. The standard graph can be obtained, or the semi-logarithmic graph can be obtained.

```python
import os
import pm4py

log_path = os.path.join("tests", "input_data", "roadtraffic100traces.xes")

if __name__ == "__main__":
	log = pm4py.read_xes(log_path)
	log = pm4py.convert_to_event_log(log)

	from pm4py.algo.filtering.log.attributes import attributes_filter

	x, y = attributes_filter.get_kde_numeric_attribute(log, "amount")

	from pm4py.visualization.graphs import visualizer as graphs_visualizer

	gviz = graphs_visualizer.apply_plot(x, y, variant=graphs_visualizer.Variants.ATTRIBUTES)
	graphs_visualizer.view(gviz)

	from pm4py.visualization.graphs import visualizer as graphs_visualizer

	gviz = graphs_visualizer.apply_semilogx(x, y, variant=graphs_visualizer.Variants.ATTRIBUTES)
	graphs_visualizer.view(gviz)
```

## Dotted Chart

The dotted chart is a classic visualization of the events within an event log across different dimensions. Each event in the event log corresponds to a point. The dimensions are projected on a graph with:

- **X-axis**: the values of the first dimension are represented here.

- **Y-axis**: the values of the second dimension are represented here.

- **Color**: the values of the third dimension are represented as different colors for the points of the dotted chart.

Values can be either string, numeric, or date values, and are managed accordingly by the dotted chart.

The dotted chart can be built on different attributes. A convenient choice for the dotted chart is to visualize the distribution of cases and events over time, with the following choices:

- **X-axis**: the timestamp of the event.

- **Y-axis**: the index of the case in the event log.

- **Color**: the activity of the event.

This choice allows visually identifying patterns such as:

- Batches.

- Variations in the case arrival rate.

- Variations in the case finishing rate.

In the following examples, we will build and visualize the dotted chart based on different selections of attributes (default and custom).

To build the default dotted chart on the receipt event log, the following code can be used:

```python
import pm4py
import os

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "receipt.xes"))
	pm4py.view_dotted_chart(log, format="svg")
```

To build the dotted chart on the receipt event log representing as different dimensions the "concept:name" (activity), "org:resource" (organizational resource), and "org:group" (organizational group), the following code can be used:

```python
import pm4py
import os

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "receipt.xes"))
	pm4py.view_dotted_chart(log, format="svg", attributes=["concept:name", "org:resource", "org:group"])
```

## Events Distribution

Observing the distribution of events over time allows inferring useful information about work shifts, working days, and periods of the year that are more or less busy.

The distribution of events over time can be visualized as follows. An event log is loaded, and the distribution over hours of the day, days of the week, days of the month, months, or years is calculated.

```python
import pm4py
import os

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "receipt.xes"))
	pm4py.view_events_distribution_graph(log, distr_type="days_week", format="svg")
```

The possible values for the parameter `distr_type` are:

- **hours**: plots the distribution over the hours of a day.

- **days_week**: plots the distribution over the days of a week.

- **days_month**: plots the distribution over the days of a month.

- **months**: plots the distribution over the months of a year.

- **years**: plots the distribution over the different years of the log.

## Detection of Batches

We say that an **activity** is executed in batches by a given **resource** when the resource executes the same activity multiple times in a short period.

Identifying such activities can highlight process points that can be automated, as the person's activity may be repetitive.

An example calculation on an event log follows.

```python
import pm4py
import os

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "receipt.xes"))
	from pm4py.algo.discovery.batches import algorithm
	batches = algorithm.apply(log)
```

The results can be printed on the screen as follows:

```python
if __name__ == "__main__":
	for act_res in batches:
		print("")
		print("activity: " + act_res[0][0] + " resource: " + act_res[0][1])
		print("number of distinct batches: " + str(act_res[1]))
		for batch_type in act_res[2]:
			print(batch_type, len(act_res[2][batch_type]))
```

There are indeed different types of batches detected by our method:

- **Simultaneous**: all events in the batch have identical start and end timestamps.

- **Batching at start**: all events in the batch have identical start timestamps.

- **Batching at end**: all events in the batch have identical end timestamps.

- **Sequential batching**: for all consecutive events, the end of the first is equal to the start of the second.

- **Concurrent batching**: for all consecutive events that are not sequentially matched.

## Rework (Activities)

The rework statistic identifies activities that have been repeated during the same process execution. This reveals underlying inefficiencies in the process.

In our implementation, rework takes into account an event log or Pandas dataframe and returns a dictionary associating each activity with the number of cases containing rework for that activity.

An example calculation on an event log follows.

```python
import pm4py
import os

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "receipt.xes"))
	rework = pm4py.get_rework_cases_per_activity(log)
```

## Rework (Cases)

We define rework at the case level as the number of events in a case that have an activity which has appeared previously in the case.

For example, if a case contains the following activities: A, B, A, B, C, D; the rework is 2 since the events in positions 3 and 4 refer to activities that have already been included previously.

The rework statistic can be useful to identify cases in which many events are repetitions of activities already performed.

An example calculation on an event log follows. At the end of the computation, `dictio` will contain the following entries for the six cases of the running example log:

{'3': {'number_activities': 9, 'rework': 2}, '2': {'number_activities': 5, 'rework': 0}, '1': {'number_activities': 5, 'rework': 0}, '6': {'number_activities': 5, 'rework': 0}, '5': {'number_activities': 13, 'rework': 7}, '4': {'number_activities': 5, 'rework': 0}}

```python
import pm4py
from pm4py.statistics.rework.cases.log import get as cases_rework_get

if __name__ == "__main__":
	log = pm4py.read_xes("tests/input_data/running-example.xes")
	log = pm4py.convert_to_event_log(log)

	dictio = cases_rework_get.apply(log)
```

## Query Structure - Paths over Time

We provide a feature to include information about the paths contained in the event log in a data structure that is convenient for querying at a specific point in time or within an interval. This is done using an interval tree data structure.

This can be useful to quickly compute the workload of resources in a given interval of time or to measure the number of open cases in a time interval.

To transform the event log into an interval tree, the following code can be used:

```python
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes("tests/input_data/receipt.xes")

	from pm4py.algo.transformation.log_to_interval_tree import algorithm as log_to_interval_tree

	it = log_to_interval_tree.apply(log)
```

The following example uses the data structure to compute the workload (number of events) for every resource in the specified interval.

```python
from collections import Counter
if __name__ == "__main__":
	intersecting_events = it[1318333540:1318333540+30*86400]
	res_workload = Counter(x.data["target_event"]["org:resource"] for x in intersecting_events)
```

The following example uses the data structure to compute, for each directly-follows path, the number of cases that are open in the path.

```python
from collections import Counter
if __name__ == "__main__":
	intersecting_events = it[1318333540:1318333540+30*86400]
	open_paths = Counter((x.data["source_event"]["concept:name"], x.data["target_event"]["concept:name"]) for x in intersecting_events)
```

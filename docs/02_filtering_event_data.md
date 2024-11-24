# Filtering Event Data

PM4Py also has various specific methods to filter an event log.

## Filtering on timeframe

In the following paragraph, various methods regarding filtering with time frames are present. For each of the methods, the log and Pandas DataFrame methods are revealed. One might be interested in only keeping the traces that are contained in a specific interval, e.g., 09 March 2011 and 18 January 2012.

```python
import pm4py
if __name__ == "__main__":
	filtered_log = pm4py.filter_time_range(log, "2011-03-09 00:00:00", "2012-01-18 23:59:59", mode='traces_contained')
```

However, it is also possible to keep the traces that are intersecting with a time interval.

```python
import pm4py
if __name__ == "__main__":
	filtered_log = pm4py.filter_time_range(log, "2011-03-09 00:00:00", "2012-01-18 23:59:59", mode='traces_intersecting')
```

Until now, only trace-based techniques have been discussed. However, there is a method to keep the events that are contained in a specific timeframe.

```python
import pm4py
if __name__ == "__main__":
	filtered_log = pm4py.filter_time_range(log, "2011-03-09 00:00:00", "2012-01-18 23:59:59", mode='events')
```

## Filter on case performance

This filter permits to keep only traces with duration that is inside a specified interval. In the examples, traces between 1 and 10 days are kept. Note that the time parameters are given in seconds.

```python
import pm4py
if __name__ == "__main__":
	filtered_log = pm4py.filter_case_performance(log, 86400, 864000)
```

## Filter on start activities

In general, PM4Py is able to filter a log or a DataFrame on start activities. First of all, it might be necessary to know the starting activities. Therefore, code snippets are provided. Subsequently, an example of filtering is provided. The first snippet works with a log object, the second one works on a DataFrame.

`log_start` is a dictionary that contains the activity as key and the number of occurrences as value.

```python
import pm4py
if __name__ == "__main__":
	log_start = pm4py.get_start_activities(log)
	filtered_log = pm4py.filter_start_activities(log, ["S1"]) #suppose "S1" is the start activity you want to filter on
```

## Filter on end activities

In general, PM4Py offers the possibility to filter a log or a DataFrame on end activities. This filter permits keeping only traces with an end activity among a set of specified activities. First of all, it might be necessary to know the end activities. Therefore, a code snippet is provided.

```python
import pm4py
if __name__ == "__main__":
	end_activities = pm4py.get_end_activities(log)
	filtered_log = pm4py.filter_end_activities(log, ["pay compensation"])
```

## Filter on variants

A variant is a set of cases that share the same control-flow perspective, meaning a set of cases that share the same classified events (activities) in the same order. In this section, we will focus first on log objects for all methods, then continue with the DataFrame. To retrieve the variants from the log, the following code snippet can be used:

```python
import pm4py
if __name__ == "__main__":
	variants = pm4py.get_variants(log)
```

To filter on a given collection of variants, the following code snippet can be used:

```python
import pm4py
if __name__ == "__main__":
	variants = pm4py.filter_variants(log, ["A,B,C,D", "A,E,F,G", "A,C,D"])
```

Other variant-based filters are offered. The filters on the top-k variants keep in the log only the cases following one of the k most frequent variants:

```python
import pm4py
if __name__ == "__main__":
	log = pm4py.read_xes("tests/input_data/receipt.xes")
	k = 2
	filtered_log = pm4py.filter_variants_top_k(log, k)
```

The filters on variants coverage keep the cases following the top variants of the log, under the condition that each variant covers the specified percentage of cases in the log. If `min_coverage_percentage=0.4`, and we have a log with 1000 cases, of which 500 are variant 1, 400 are variant 2, and 100 are variant 3, the filter keeps only the traces of variant 1 and variant 2.

```python
import pm4py
if __name__ == "__main__":
	log = pm4py.read_xes("tests/input_data/receipt.xes")
	perc = 0.1
	filtered_log = pm4py.filter_variants_by_coverage_percentage(log, perc)
```

## Filter on attribute values

Filtering on attribute values permits, alternatively, to:

- Keep cases that contain at least one event with one of the given attribute values,
- Remove cases that contain an event with one of the given attribute values,
- Keep events (trimming traces) that have one of the given attribute values,
- Remove events (trimming traces) that have one of the given attribute values.

Examples of attributes are the resource (generally contained in the `org:resource` attribute) and the activity (generally contained in the `concept:name` attribute). As noted before, the first method can be applied to log objects, the second to DataFrame objects. To get the list of resources and activities contained in the log, the following code could be used.

```python
import pm4py
if __name__ == "__main__":
	activities = pm4py.get_event_attribute_values(log, "concept:name")
	resources = pm4py.get_event_attribute_values(log, "org:resource")
```

To filter traces containing/not containing a given list of resources, the following code could be used.

```python
if __name__ == "__main__":
	tracefilter_log_pos = pm4py.filter_event_attribute_values(log, "org:resource", ["Resource10"], level="case", retain=True)
	tracefilter_log_neg = pm4py.filter_event_attribute_values(log, "org:resource", ["Resource10"], level="case", retain=False)
```

It is also possible to keep only the events performed by a given list of resources (trimming the cases). The following code can be used.

```python
if __name__ == "__main__":
	tracefilter_log_pos = pm4py.filter_event_attribute_values(log, "org:resource", ["Resource10"], level="event", retain=True)
	tracefilter_log_neg = pm4py.filter_event_attribute_values(log, "org:resource", ["Resource10"], level="event", retain=False)
```

## Filter on numeric attribute values

Filtering on numeric attribute values provides options similar to filtering on string attribute values (which we have already considered). First, we import the log. Subsequently, we want to keep only the events satisfying an amount comprised between 34 and 36. An additional filter aims to keep only cases with at least one event satisfying the specified amount. The filter on cases provides the option to specify up to two attributes that are checked on the events that shall satisfy the numeric range. For example, if we are interested in cases having an event with the activity "Add penalty" that has an amount between 34 and 500, a code snippet is also provided.

```python
import os
import pandas as pd
import pm4py

if __name__ == "__main__":
	df = pd.read_csv(os.path.join("tests", "input_data", "roadtraffic100traces.csv"))
	df = pm4py.format_dataframe(df)

	from pm4py.algo.filtering.pandas.attributes import attributes_filter
	filtered_df_events = attributes_filter.apply_numeric_events(df, 34, 36,
												 parameters={attributes_filter.Parameters.CASE_ID_KEY: "case:concept:name", attributes_filter.Parameters.ATTRIBUTE_KEY: "amount"})

	filtered_df_cases = attributes_filter.apply_numeric(df, 34, 36,
												 parameters={attributes_filter.Parameters.CASE_ID_KEY: "case:concept:name", attributes_filter.Parameters.ATTRIBUTE_KEY: "amount"})

	filtered_df_cases = attributes_filter.apply_numeric(df, 34, 500,
												 parameters={attributes_filter.Parameters.CASE_ID_KEY: "case:concept:name", attributes_filter.Parameters.ATTRIBUTE_KEY: "amount",
															 attributes_filter.Parameters.STREAM_FILTER_KEY1: "concept:name",
															 attributes_filter.Parameters.STREAM_FILTER_VALUE1: "Add penalty"})
```

## Between Filter

The between filter transforms the event log by identifying, in the current set of cases, all the subcases that go from a source activity to a target activity. This is useful to analyze in detail the behavior in the log between such a pair of activities (e.g., the throughput time, which activities are included, the level of conformance). The between filter between two activities is applied as follows.

```python
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes("tests/input_data/running-example.xes")

	filtered_log = pm4py.filter_between(log, "check ticket", "decide")
```

## Case Size Filter

The case size filter keeps only the cases in the log with a number of events included in a range that is specified by the user. This can have two purposes: eliminating cases that are too short (which are obviously incomplete or outliers) or are too long (too much rework). The case size filter can be applied as follows:

```python
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes("tests/input_data/running-example.xes")

	filtered_log = pm4py.filter_case_size(log, 5, 10)
```

## Rework Filter

The filter described in this section aims to identify cases where a given activity has been repeated. The rework filter is applied as follows. In this case, we search for all cases having at least 2 occurrences of the activity "reinitiate request."

```python
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes("tests/input_data/running-example.xes")

	filtered_log = pm4py.filter_activities_rework(log, "reinitiate request", 2)
```

## Paths Performance Filter

The paths performance filter identifies the cases in which a given path between two activities takes a duration that is within a range specified by the user. This can be useful to identify cases in which a large amount of time has passed between two activities. The paths filter is applied as follows. In this case, we are looking for cases containing at least one occurrence of the path between "decide" and "pay compensation" having a duration between 2 days and 10 days (where each day has a duration of 86400 seconds).

```python
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes("tests/input_data/running-example.xes")

	filtered_log = pm4py.filter_paths_performance(log, ("decide", "pay compensation"), 2*86400, 10*86400)
```
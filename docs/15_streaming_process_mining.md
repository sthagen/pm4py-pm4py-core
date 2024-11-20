

# Streaming Process Mining




## Streaming Package General Structure


In pm4py, we offer support for streaming process mining functionalities, including:,

- Streaming process discovery (DFG),

- Streaming conformance checking (footprints and TBR),

- Streaming importing of XES/CSV files
The management of the stream of events is done by the 
pm4py.streaming.stream.live_event_stream.LiveEventStream
class.
This class provides access to two methods:
,

- register(algo)
: registers a new algorithm to the live event stream (that will be
notified when an event is added to the stream.
,

- append(event):
 adds an event to the live event stream.
The 
LiveEventStream
 processes the incoming events using a thread pool. This helps to
manage a “flood” of events using a given number of different threads.

For the streaming algorithms, that are registered to the LiveEventStream, we provide an
interface that should be implemented. The following methods should be implemented inside each
streaming algorithm:,

- _process(event)
: a method that accepts and process an incoming event.,

- _current_result()
: a method that returns the current state of the streaming
algorithm.



## Streaming Process Discovery (Directly-Follows Graph)


The following example will show how to discover a DFG from a stream of events.
Let’s first define the (live) event stream:



```python
from pm4py.streaming.stream.live_event_stream import LiveEventStream

if __name__ == "__main__":
	live_event_stream = LiveEventStream()
```


Then, create the streaming DFG discovery object (that will contain the list of activities
and relationships inside the DFG):



```python
from pm4py.streaming.algo.discovery.dfg import algorithm as dfg_discovery

if __name__ == "__main__":
	streaming_dfg = dfg_discovery.apply()
```


Then, we need to register the streaming DFG discovery to the stream:



```python
if __name__ == "__main__":
	live_event_stream.register(streaming_dfg)
```


And start the stream:



```python
if __name__ == "__main__":
	live_event_stream.start()
```


To put some known event log in the stream, we need to import a XES log:



```python
import os
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "running-example.xes"))
```


And then convert that to a static event stream:



```python
import pm4py

if __name__ == "__main__":
	static_event_stream = pm4py.convert_to_event_stream(log)
```


Then, we can add all the events to the live stream:



```python
if __name__ == "__main__":
	for ev in static_event_stream:
		live_event_stream.append(ev)
```


Then, stopping the stream, we make sure that the events in the queue are fully processed:



```python
if __name__ == "__main__":
	live_event_stream.stop()
```


At the end, we can get the directly-follows graph, along with the activities of the graph,
the set of start and end activities, by doing:



```python
if __name__ == "__main__":
	dfg, activities, sa, ea = streaming_dfg.get()
```


If we do print(dfg) on the running-example.xes log we obtain:
{(‘register request’, ‘examine casually’): 3, (‘examine casually’, ‘check ticket’): 4,
(‘check ticket’, ‘decide’): 6, (‘decide’, ‘reinitiate request’): 3, (‘reinitiate request’,
‘examine thoroughly’): 1, (‘examine thoroughly’, ‘check ticket’): 2, (‘decide’, ‘pay
compensation’): 3, (‘register request’, ‘check ticket’): 2, (‘check ticket’, ‘examine
casually’): 2, (‘examine casually’, ‘decide’): 2, (‘register request’, ‘examine
thoroughly’): 1, (‘decide’, ‘reject request’): 3, (‘reinitiate request’, ‘check ticket’): 1,
(‘reinitiate request’, ‘examine casually’): 1, (‘check ticket’, ‘examine thoroughly’): 1,
(‘examine thoroughly’, ‘decide’): 1}



## Streaming Conformance Checking (TBR)


The following examples will show how to check conformance against a stream of events with the
footprints and token-based replay algorithms. For both the examples that follow, we assume to
work with the 
running-example.xes
 log and with a log discovered using inductive miner
infrequent with the default noise threshold (0.2).

The following code can be used to import the running-example.xes log



```python
import os
import pm4py
if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "receipt.xes"))
```


And convert that to a static stream of events:



```python
import pm4py
if __name__ == "__main__":
	static_event_stream = pm4py.convert_to_event_stream(log)
```


Then, the following code can be used to discover a process tree using the inductive miner:



```python
import pm4py
if __name__ == "__main__":
	tree = pm4py.discover_process_tree_inductive(log)
```


And convert that to a Petri net:



```python
import pm4py
if __name__ == "__main__":
	net, im, fm = pm4py.convert_to_petri_net(tree)
```


Now, we can apply the streaming TBR.
Then, we create a live event stream:



```python
from pm4py.streaming.stream.live_event_stream import LiveEventStream
if __name__ == "__main__":
	live_event_stream = LiveEventStream()
```


And the streaming token-based replay algorithm:



```python
from pm4py.streaming.algo.conformance.tbr import algorithm as tbr_algorithm
if __name__ == "__main__":
	streaming_tbr = tbr_algorithm.apply(net, im, fm)
```


Moreover, we can register that to the live event stream:



```python
if __name__ == "__main__":
	live_event_stream.register(streaming_tbr)
```


And start the live event stream:



```python
if __name__ == "__main__":
	live_event_stream.start()
```


After that, we can add each event of the log to the live event stream:



```python
if __name__ == "__main__":
	for ev in static_event_stream:
		live_event_stream.append(ev)
```


And then, stop the event stream:



```python
if __name__ == "__main__":
	live_event_stream.stop()
```


And get statistics on the execution of the replay (how many missing tokens were needed?) as
a Pandas dataframe. This method can be called throughout the lifecycle of the stream,
providing the “picture” of the replay up to that point:



```python
if __name__ == "__main__":
	conf_stats = streaming_tbr.get()
	print(conf_stats)
```


In addition to this, the following methods are available inside the streaming TBR that print
some warning during the replay. The methods can be overriden easily (for example, to send the
message with mail):,

- message_case_or_activity_not_in_event,

- message_activity_not_possible,

- message_missing_tokens,

- message_case_not_in_dictionary,

- message_final_marking_not_reached


## Streaming Conformance Checking (footprints)


Footprints is another conformance checking method offered in pm4py, which can be implemented in
the context of streaming events. In the following, we see an application of the streaming
footprints.
First of all, we can discover the footprints from the process model:



```python
if __name__ == "__main__":
	from pm4py.algo.discovery.footprints import algorithm as fp_discovery
	footprints = fp_discovery.apply(tree)
```


Then, we can create the live event stream:



```python
if __name__ == "__main__":
	from pm4py.streaming.stream.live_event_stream import LiveEventStream
	live_event_stream = LiveEventStream()
```


Then, we can create the streaming footprints object:



```python
if __name__ == "__main__":
	from pm4py.streaming.algo.conformance.footprints import algorithm as fp_conformance
	streaming_footprints = fp_conformance.apply(footprints)
```


And register that to the stream:



```python
if __name__ == "__main__":
	live_event_stream.register(streaming_footprints)
```


After that, we can start the live event stream:



```python
if __name__ == "__main__":
	live_event_stream.start()
```


And append every event of the original log to this live event stream:



```python
if __name__ == "__main__":
	for ev in static_event_stream:
		live_event_stream.append(ev)
```


Eventually, we can stop the live event stream:



```python
if __name__ == "__main__":
	live_event_stream.stop()
```


And get the statistics of conformance checking:



```python
if __name__ == "__main__":
	conf_stats = streaming_footprints.get()
	print(conf_stats)
```


In addition to this, the following methods are available inside the streaming footprints that
print some warning during the replay. The methods can be overriden easily (for example, to send
the message with mail):,

- message_case_or_activity_not_in_event,

- message_activity_not_possible,

- message_footprints_not_possible,

- message_start_activity_not_possible,

- message_end_activity_not_possible,

- message_case_not_in_dictionary


## Streaming Conformance Checking (Temporal Profile)


We propose in pm4py an implementation of the temporal profile model. This has been described in:
Stertz, Florian, Jürgen Mangler, and Stefanie Rinderle-Ma. "Temporal Conformance Checking at Runtime based on Time-infused Process Models." arXiv preprint arXiv:2008.07262 (2020).
A temporal profile measures for every couple of activities in the log the average time and the standard deviation between events having the
provided activities. The time is measured between the completion of the first event and the start of the second event. Hence, it is assumed to work with an interval log
where the events have two timestamps. The output of the temporal profile discovery is a dictionary where each couple of activities (expressed as a tuple)
is associated to a couple of numbers, the first is the average and the second is the average standard deviation.
It is possible to use a temporal profile to perform conformance checking on an event log.
The times between the couple of activities in the log are assessed against the numbers stored in the temporal profile. Specifically,
a value is calculated that shows how many standard deviations the value is different from the average. If that value exceeds a threshold (by default set to 
6
,
according to the six-sigma principles), then the couple of activities is signaled.
In pm4py, we provide a streaming conformance checking algorithm based on the temporal profile.
The algorithm checks an incoming event against every event that happened previously in the case,
identifying deviations according to the temporal profile. This section provides an example where
a temporal profile is discovered, the streaming conformance checking is set-up and actually a log
is replayed on the stream.
We can load an event log, and apply the discovery algorithm.



```python
import pm4py
from pm4py.algo.discovery.temporal_profile import algorithm as temporal_profile_discovery

if __name__ == "__main__":
	log = pm4py.read_xes("tests/input_data/running-example.xes")
	temporal_profile = temporal_profile_discovery.apply(log)
```


We create the stream, register the temporal conformance checking algorithm and start the stream.
The conformance checker can be created with some parameters.

See Parameters



```python
from pm4py.streaming.stream.live_event_stream import LiveEventStream
from pm4py.streaming.algo.conformance.temporal import algorithm as temporal_conformance_checker

if __name__ == "__main__":
	stream = LiveEventStream()
	temp_cc = temporal_conformance_checker.apply(temporal_profile)
	stream.register(temp_cc)
	stream.start()
```




|Parameter Key|Type|Default|Description|
|---|---|---|---|
|Parameters.CASE_ID_KEY|string|case:concept:name|The attribute to use as case ID.|
|Parameters.ACTIVITY_KEY|string|concept:name|The attribute to use as activity.|
|Parameters.START_TIMESTAMP_KEY|string|start_timestamp|The attribute to use as start timestamp.|
|Parameters.TIMESTAMP_KEY|string|time:timestamp|The attribute to use as timestamp.|
|Parameters.ZETA|int|6|Multiplier for the standard deviation. Couples of events that are more distant than this are signaled by the temporal profile.|



We send the events of the log against the stream:



```python
if __name__ == "__main__":
	static_stream = pm4py.convert_to_event_stream(log)
	for event in static_stream:
		stream.append(event)
```


During the execution of the streaming temporal profile conformance checker, some warnings
are printed if a couple of events violate the temporal profile. Moreover, it is also possible to get
a dictionary containing the cases with deviations associated with all their deviations.
The following code is useful to get the results of the streaming temporal profile conformance
checking.



```python
if __name__ == "__main__":
	stream.stop()
	res = temp_cc.get()
```




## Streaming Importer (XES trace-by-trace)


In order to be able to process the traces of a XES event log that might not fit in the memory,
or when a sample of a big log is needed, the usage of the XES trace-by-trace streaming importer
helps to cope with the situation.
The importer can be used in a natural way, providing the path to the log:



```python
from pm4py.streaming.importer.xes import importer as xes_importer

if __name__ == "__main__":
	streaming_log_object = xes_importer.apply(os.path.join("tests", "input_data", "running-example.xes"), variant=xes_importer.Variants.XES_TRACE_STREAM)
```


And it is possible to iterate over the traces of this log (that are read trace-by-trace):



```python
if __name__ == "__main__":
	for trace in streaming_log_object:
		print(trace)
```




## Streaming Importer (XES event-by-event)


In order to be able to process the events of a XES event log that might not fit in the memory,
or when the sample of a big log is needed, the usage of the XES event-by-event streaming
importer helps to cope with the situation. In this case, the single events inside the traces are
picked during the iteration.
The importer can be used in a natural way, providing the path to the log:



```python
from pm4py.streaming.importer.xes import importer as xes_importer

if __name__ == "__main__":
	streaming_ev_object = xes_importer.apply(os.path.join("tests", "input_data", "running-example.xes"), variant=xes_importer.Variants.XES_EVENT_STREAM)
```


And it is possible to iterate over the single events of this log (that are read during the
iteration):



```python
if __name__ == "__main__":
	for event in streaming_ev_object:
		print(event)
```




## Streaming Importer (CSV event-by-event)


In order to be able to process the events of a CSV event log that might not fit in the memory,
or when the sample of a big log is needed, Pandas might not be feasible. In this case, the
single rows of the CSV file are parsed during the iteration.
The importer can be used in a natural way, providing the path to a CSV log:



```python
from pm4py.streaming.importer.csv import importer as csv_importer
if __name__ == "__main__":
	log_object = csv_importer.apply(os.path.join("tests", "input_data", "running-example.csv"))
```


And it is possible to iterate over the single events of this log (that are read during the
iteration):



```python
if __name__ == "__main__":
	for ev in log_object:
		print(ev)
```




## OCEL streaming


We offer support for streaming on OCEL. The support is currently limited to:,

- Iterating over the events of an OCEL.,

- Listening to OCELs to direct them to traditional event listeners.
One can iterate over the events of an OCEL as follows:



```python
import pm4py
import os
from pm4py.objects.ocel.util import ocel_iterator

if __name__ == "__main__":
	ocel = pm4py.read_ocel(os.path.join("tests", "input_data", "ocel", "example_log.jsonocel"))
	for ev in ocel_iterator.apply(ocel):
		print(ev)
```


A complete example in which we take an OCEL, we instantiate two event streams
for the 
order
 and 
element
 object types respectively, and we
push to them the flattening of the events of the OCEL, is reported on the right.
The two event listeners are attached with a printer, such that the flattened
event is printed on the screen whenever received.



```python
import pm4py
import os
from pm4py.streaming.stream import live_event_stream
from pm4py.streaming.util import event_stream_printer
from pm4py.streaming.conversion import ocel_flatts_distributor
from pm4py.objects.ocel.util import ocel_iterator

if __name__ == "__main__":
	ocel = pm4py.read_ocel(os.path.join("tests", "input_data", "ocel", "example_log.jsonocel"))
	# we wants to use the traditional algorithms for streaming also on object-centric event logs.
	# for this purpose, first we create two different event streams, one for the "order" object type
	# and one for the "element" object type.
	order_stream = live_event_stream.LiveEventStream()
	element_stream = live_event_stream.LiveEventStream()
	# Then, we register an algorithm for every one of them, which is a simple printer of the received events.
	order_stream_printer = event_stream_printer.EventStreamPrinter()
	element_stream_printer = event_stream_printer.EventStreamPrinter()
	order_stream.register(order_stream_printer)
	element_stream.register(element_stream_printer)
	# Then, we create the distributor object.
	# This registers different event streams for different object types.
	flatts_distributor = ocel_flatts_distributor.OcelFlattsDistributor()
	flatts_distributor.register("order", order_stream)
	flatts_distributor.register("element", element_stream)
	order_stream.start()
	element_stream.start()
	# in this way, we iterate over the events of an OCEL
	for ev in ocel_iterator.apply(ocel):
		# and the OCEL event is sent to all the "flattened" event streams.
		flatts_distributor.append(ev)
		# since the "flattened" event streams register a printer each, what we get is a print
		# of all the events that reach these instances.
	order_stream.stop()
	element_stream.stop()
```


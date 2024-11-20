

# Object-Centric Event Logs


In pm4py we offer support for object-centric event logs (importing/exporting).


## Motivation


Traditional event logs, used by mainstream process mining techniques, require
the events to be related to a 
case
. A case is a set of events for a particular
purpose. A 
case notion
 is a criteria to assign a case to the events.
However, in real processes this leads to two problems:,

- If we consider the Order-to-Cash process, an order could be related to many different deliveries.
If we consider the delivery as case notion, the same event of 
Create Order
 needs to be
replicated in different cases (all the deliveries involving the order). This is called the

convergence
 problem.,

- If we consider the Order-to-Cash process, an order could contain different order items,
each one with a different lifecycle. If we consider the order as case notion, several instances
of the activities for the single items may be contained in the case, and this make the
frequency/performance annotation of the process problematic. This is called the 
divergence
problem.
Object-centric event logs
 relax the assumption that an event is related to exactly
one case. Indeed, an event can be related to different 
objects
 of different 
object types
.
Essentially, we can describe the different components of an object-centric event log as:,

- Events
, having an identifier, an activity, a timestamp, a list of related objects and a
dictionary of other attributes.,

- Objects
, having an identifier, a type and a dictionary of other attributes.,

- Attribute names
, e.g., the possible keys for the attributes of the event/object attribute map.,

- Object types
, e.g., the possible types for the objects.


## Supported Formats


Several historical formats (OpenSLEX, XOC) have been proposed for the storage of object-centric
event logs. In particular, the 
OCEL standard (http://www.ocel-standard.org)
 proposes
lean and intercompatible formats for the storage of object-centric event logs. These include:,

- XML-OCEL
: a storage format based on XML for object-centric event logs.
An example of XML-OCEL event log is reported 
here (https://github.com/pm4py/pm4py-core/blob/release/tests/input_data/ocel/example_log.xmlocel)
.,

- JSON-OCEL
: a storage format based on JSON for object-centric event logs.
An example of JSON-OCEL event log is reported 
here (https://github.com/pm4py/pm4py-core/blob/release/tests/input_data/ocel/example_log.jsonocel)
.
Among the commonalities of these formats, the event/object identifier is 
ocel:id
,
the activity identifier is 
ocel:activity
, the timestamp of the event is 
ocel:timestamp
,
the type of the object is 
ocel:type
.
Moreover, the list of related objects for the events is identified by 
ocel:omap
,
the attribute map for the events is identified by 
ocel:vmap
, the attribute map for the
objects is identified by 
ocel:ovmap
.
Ignoring the attributes at the object level, we can also represent the object-centric event log
in a CSV format (an example is reported 
here (https://github.com/pm4py/pm4py-core/blob/release/tests/input_data/ocel/example_log.csv)
). There, a row represent an event, where the event identifier is 
ocel:eid
,
and the related objects for a given type OTYPE are reported as a list under the voice 
ocel:type:OTYPE
.


## Importing/Export OCELs


For all the supported formats, an OCEL event log can be read by doing:


```python
import pm4py

if __name__ == "__main__":
	path = "tests/input_data/ocel/example_log.jsonocel"
	ocel = pm4py.read_ocel(path)
```


An OCEL can also be exported easily by doing (
ocel
 is assumed to be an
object-centric event log):


```python
import pm4py

if __name__ == "__main__":
	path = "./output.jsonocel"
	pm4py.write_ocel(ocel, path)
```




## Basic Statistics on OCELs


We offer some basic statistics that can be calculated on OCELs.
The simplest way of obtaining some statistics on OCELs is by doing the print of the OCEL object:


```python
if __name__ == "__main__":
	print(ocel)
```


In the previous case, some statistics will be printed as follows:
Object-Centric Event Log (number of events: 23, number of objects: 15, number of activities: 15, number of object types: 3, events-objects relationships: 39)
Activities occurrences: {'Create Order': 3, 'Create Delivery': 3, 'Delivery Successful': 3, 'Invoice Sent': 2, 'Payment Reminder': 2, 'Confirm Order': 1, 'Item out of Stock': 1, 'Item back in Stock': 1, 'Delivery Failed': 1, 'Retry Delivery': 1, 'Pay Order': 1, 'Remove Item': 1, 'Cancel Order': 1, 'Add Item to Order': 1, 'Send for Credit Collection': 1}
Object types occurrences: {'element': 9, 'order': 3, 'delivery': 3}
Please use ocel.get_extended_table() to get a dataframe representation of the events related to the objects.
The retrieval of the names of the attributes in the log can be obtained
doing:


```python
if __name__ == "__main__":
	attribute_names = pm4py.ocel_get_attribute_names(ocel)
```


The retrieval of the object types contained in the event log can be otained
doing:


```python
if __name__ == "__main__":
	attribute_names = pm4py.ocel_get_object_types(ocel)
```


The retrieval of a dictionary containing the set of activities for each object type
can be obtained using the command on the right. In this case, the key
of the dictionary will be the object type, and the value the set of activities
which appears for the object type.


```python
if __name__ == "__main__":
	object_type_activities = pm4py.ocel_object_type_activities(ocel)
```


It is possible to obtain for each event identifier and object type the number of related
objects to the event. The output will be a dictionary where the first key will be
the event identifier, the second key will be the object type and the value will
be the number of related objects per type.


```python
if __name__ == "__main__":
	ocel_objects_ot_count = pm4py.ocel_objects_ot_count(ocel)
```


It is possible to calculate the so-called 
temporal summary
 of the object-centric event log.
The temporal summary is a table (dataframe) in which the different timestamps occurring in the log are reported
along with the set of activities happening in a given point of time and the objects involved in such



```python
if __name__ == "__main__":
	temporal_summary = pm4py.ocel_temporal_summary(ocel)
```


It is possible to calculate the so-called 
objects summary
 of the object-centric event log.
The objects summary is a table (dataframe) in which the different objects occurring in the log are reported
along with the list of activities of the events related to the object, the start/end timestamps
of the lifecycle, the duration of the lifecycle and the other objects related to the given object
in the interaction graph.



```python
if __name__ == "__main__":
	temporal_summary = pm4py.ocel_objects_summary(ocel)
```




## Internal Data Structure


In this section, we describe the data structure used in pm4py to store object-centric event logs.
We have in total three Pandas dataframes:,

- The 
events
 dataframe: this stores a row for each event. Each row contains
the event identifier (
ocel:eid
), the activity (
ocel:activity
),
the timestamp (
ocel:timestamp
), and the values for the other event attributes (one per column).,

- The 
objects
 dataframe: this stores a row for each object. Each row contains
the object identifier (
ocel:oid
), the type (
ocel:type
),
and the values for the object attributes (one per column).,

- The 
relations
 dataframe: this stores a row for every relation event->object.
Each row contains the event identifier (
ocel:eid
), the object identifier
(
ocel:oid
), the type of the related object (
ocel:type
).
These dataframes can be accessed as properties of the OCEL object (e.g.,
ocel.events
, 
ocel.objects
, 
ocel.relations
), and be obviously used
for any purposes (filtering, discovery).


## Filtering Object-Centric Event Logs


In this section, we describe some filtering operations available in pm4py and specific for
object-centric event logs. There are filters at three levels:,

- Filters at the event level (operating first at the 
ocel.events
 structure and then propagating
the result to the other parts of the object-centric log).,

- Filters at the object level (operating first at the 
ocel.objects
 structure and then propagating
the result to the other parts of the object-centric log).,

- Filters at the relations level (operating first at the 
ocel.relations
 structure and then propagating
the result to the other parts of the object-centric log).


### Filter on Event Attributes


We can keep the events with a given attribute falling inside the specified list
of values by using 
pm4py.filter_ocel_event_attribute
.
An example, filtering on the 
ocel:activity
 (the activity) attribute
is reported on the right. The 
positive
 boolean tells if to filter the events
with an activity falling in the list or to filter the events NOT falling in the
specified list (if positive is False).


```python
if __name__ == "__main__":
	filtered_ocel = pm4py.filter_ocel_event_attribute(ocel, "ocel:activity", ["Create Fine", "Send Fine"], positive=True)
```




### Filter on Object Attributes


We can keep the objects with a given attribute falling inside the specified list
of values by using 
pm4py.filter_ocel_object_attribute
.
An example, filtering on the 
ocel:type
 (the object type) attribute
is reported on the right. The 
positive
 boolean tells if to filter the objects
with a type falling in the list or to filter the objects NOT falling in the
specified list (if positive is False).



```python
if __name__ == "__main__":
	filtered_ocel = pm4py.filter_ocel_object_attribute(ocel, "ocel:type", ["order", "delivery"], positive=True)
```




### Filter on Allowed Activities per Object Type


Sometimes, object-centric event logs include more relations between events
and objects than legit. This could lead back to the divergence problem.
We introduce a filter on the allowed activities per object type.
This helps in keeping for each activity only the meaningful object types, excluding the others.
An example application of the filter is reported on the right. In this case, we keep
for the 
order
 object type only the 
Create Order
 activity,
and for the 
item
 object type only the 
Create Order
 and

Create Delivery
 activities.


```python
if __name__ == "__main__":
	filtered_ocel = pm4py.filter_ocel_object_types_allowed_activities(ocel, {"order": ["Create Order"], "item": ["Create Order", "Create Delivery"]})
```




### Filter on the Number of Objects per Type


With this filter, we want to search for some patterns in the log (for example, the events related
to at least 
1
 order and 
2
 items). This helps in identifying exceptional patterns
(e.g., an exceptional number of related objects per event). An example is reported on the right.


```python
if __name__ == "__main__":
	filtered_ocel = pm4py.filter_ocel_object_per_type_count(ocel, {"order": 1, "element": 2})
```




### Filter on Start/End Events per Object


In some contexts, we may want to identify the events in which an object of a given
type starts/completes his lifecycle. This may pinpoint some uncompleteness
in the recordings. Examples are reported on the right.


```python
if __name__ == "__main__":
	filtered_ocel = pm4py.filter_ocel_start_events_per_object_type(ocel, "order")
	filtered_ocel = pm4py.filter_ocel_end_events_per_object_type(ocel, "order")
```




### Filter on Event Timestamp


An useful filter, to restrict the behavior of the object-centric event log
to a specific time interval, is the timestamp filter (analogous to its
traditional counterpart). An example is reported on the right.


```python
if __name__ == "__main__":
	filtered_ocel = pm4py.filter_ocel_events_timestamp(ocel, "1981-01-01 00:00:00", "1982-01-01 00:00:00", timestamp_key="ocel:timestamp")
```




### Filter on Object Types


In this filter, we want to keep a limited set of object types of the log
by manually specifying the object types to retain. Only the events related
to at least one object of a provided object type are kept.


```python
if __name__ == "__main__":
	filtered_ocel = pm4py.filter_ocel_object_types(ocel, ['order', 'element'])
```




### Filter on Event Identifiers


In this filter, we want to keep some events of the object-centric by
explicitly specifying the identifier of the same events.


```python
if __name__ == "__main__":
	filtered_ocel = pm4py.filter_ocel_events(ocel, ['e1', 'e2'])
```




### Filter on Connected Components


In this filter, we want to keep the events related to the connected component
of a provided object in the objects interaction graph. So a subset of events of the original log,
loosely interconnected, are kept in the filtered log


```python
if __name__ == "__main__":
	filtered_ocel = pm4py.filter_ocel_cc_object(ocel, 'o1')
```




### Filter on Object Identifiers


In this filter, we want to keep a subset of the objects (identifiers) of the original
object-centric event log. Therefore, only the events related to at least one of these objects
are kept in the object-centric event log.


```python
if __name__ == "__main__":
	filtered_ocel = pm4py.filter_ocel_objects(ocel, ['o1', 'i1'])
```


It's also possible to iteratively expand the set of objects of the filter to the objects
that are interconnected to the given objects in the objects interaction graph.
This is done with the parameter 
level
. An example is provided where the expansion
of the set of objects to the 'nearest' ones is done:


```python
if __name__ == "__main__":
	filtered_ocel = pm4py.filter_ocel_objects(ocel, ['o1'], level=2)
```




### Sampling on the Events


It is possible to keep a random subset of the events of the original object-centric
event log. In this case, the interactions between the objects are likely to be lost.


```python
if __name__ == "__main__":
	filtered_ocel = pm4py.sample_events(ocel, num_events=100)
```




## Flattening to a Traditional Log


Flattening
 permits to convert an object-centric event log to a traditional
event log with the specification of an object type. This allows for the application
of traditional process mining techniques to the flattened log.

An example in which an event log is imported, and a flattening operation
is applied on the 
order
 object type, is the following:


```python
import pm4py

if __name__ == "__main__":
	ocel = pm4py.read_ocel("tests/input_data/ocel/example_log.jsonocel")
	flattened_log = pm4py.ocel_flattening(ocel, "order")
```




## Timestamp-Based Interleavings


The situation in which an object-centric event log is produced directly at the extraction
phase from the information systems is uncommon. Extractors for this settings are quite uncommon
nowadays.
More frequent is the situation where some event logs can be extracted from the system
and then their cases are related. So we can use the classical extractors to extract the
event logs, and additionally extract only the relationships between the cases.
This information can be used to mine the relationships between events. In particular,
the method of 
timestamp-based interleavings
 can be used. These consider the temporal
flow between the different processes, based on the provided case relations: you can go from the
left-process to the right-process, and from the right-process to the left-process.
In the following, we will assume the cases to be Pandas dataframes (with the classical
pm4py naming convention, e.g. 
case:concept:name
, 
concept:name
 and 
time:timestamp
)
and a case relations dataframe is defined between them (with the related cases being expressed
respectively as 
case:concept:name_LEFT
 and 
case:concept:name_RIGHT
.
In this example, we load two event logs, and a dataframe containing the relationships
between them. Then, we apply the timestamp-based interleaved miner.


```python
import pandas as pd
import pm4py

if __name__ == "__main__":
	dataframe1 = pd.read_csv("tests/input_data/interleavings/receipt_even.csv")
	dataframe1 = pm4py.format_dataframe(dataframe1)
	dataframe2 = pd.read_csv("tests/input_data/interleavings/receipt_odd.csv")
	dataframe2 = pm4py.format_dataframe(dataframe2)
	case_relations = pd.read_csv("tests/input_data/interleavings/case_relations.csv")

	from pm4py.algo.discovery.ocel.interleavings import algorithm as interleavings_discovery
	interleavings = interleavings_discovery.apply(dataframe1, dataframe2, case_relations)
```


The resulting interleavings dataframe will contain several columns, including for each row (that is a couple of related events, the first belonging to the first dataframe, the second belonging to the second dataframe):,

- All the columns of the event (of the interleaving) of the first dataframe (with prefix 
LEFT
).,

- All the columns of the event (of the interleaving) of the second dataframe (with prefix 
RIGHT
).,

- The column 
@@direction
 indicating the direction of the interleaving (with 
LR
 we go left-to-right so
from the first dataframe to the second dataframe;
with 
RL
 we go right-to-left, so from the second dataframe to the first dataframe).,

- The columns 
@@source_activity
 and 
@@target_activity
 contain respectively the source and target activity of the interleaving.,

- The columns 
@@source_timestamp
 and 
@@target_timestamp
 contain respectively the source and target timestamp of the interleaving.,

- The column 
@@left_index
 contains the index of the event of the first of the two dataframes.,

- The column 
@@right_index
 contains the index of the event of the second of the two dataframes.,

- The column 
@@timestamp_diff
 contains the difference between the two timestamps (can be useful to aggregate on the time).
We provide a visualization of the interleavings between the two logs. The visualization considers
the DFG of the two logs and shows the interleavings between them (decorated by the frequency/performance
of the relationship).
An example of frequency-based interleavings visualization is reported on the right.


```python
import pandas as pd
import pm4py

if __name__ == "__main__":
	dataframe1 = pd.read_csv("tests/input_data/interleavings/receipt_even.csv")
	dataframe1 = pm4py.format_dataframe(dataframe1)
	dataframe2 = pd.read_csv("tests/input_data/interleavings/receipt_odd.csv")
	dataframe2 = pm4py.format_dataframe(dataframe2)
	case_relations = pd.read_csv("tests/input_data/interleavings/case_relations.csv")

	from pm4py.algo.discovery.ocel.interleavings import algorithm as interleavings_discovery
	interleavings = interleavings_discovery.apply(dataframe1, dataframe2, case_relations)

	from pm4py.visualization.ocel.interleavings import visualizer as interleavings_visualizer

	# visualizes the frequency of the interleavings
	gviz_freq = interleavings_visualizer.apply(dataframe1, dataframe2, interleavings, parameters={"annotation": "frequency", "format": "svg"})
	interleavings_visualizer.view(gviz_freq)
```


An example of performance-based interleavings visualization is reported on the right.


```python
import pandas as pd
import pm4py

if __name__ == "__main__":
	dataframe1 = pd.read_csv("tests/input_data/interleavings/receipt_even.csv")
	dataframe1 = pm4py.format_dataframe(dataframe1)
	dataframe2 = pd.read_csv("tests/input_data/interleavings/receipt_odd.csv")
	dataframe2 = pm4py.format_dataframe(dataframe2)
	case_relations = pd.read_csv("tests/input_data/interleavings/case_relations.csv")

	from pm4py.algo.discovery.ocel.interleavings import algorithm as interleavings_discovery
	interleavings = interleavings_discovery.apply(dataframe1, dataframe2, case_relations)

	from pm4py.visualization.ocel.interleavings import visualizer as interleavings_visualizer

	# visualizes the performance of the interleavings
	gviz_perf = interleavings_visualizer.apply(dataframe1, dataframe2, interleavings, parameters={"annotation": "performance", "aggregation_measure": "median", "format": "svg"})
	interleavings_visualizer.view(gviz_perf)
```


The parameters offered by the visualization of the interleavings follows:,

- Parameters.FORMAT
: the format of the visualization (svg, png).,

- Parameters.BGCOLOR
: background color of the visualization (default: transparent).,

- Parameters.RANKDIR
: the direction of visualization of the diagram (LR, TB).,

- Parameters.ANNOTATION
: the annotation to be used (frequency, performance).,

- Parameters.AGGREGATION_MEASURE
: the aggregation to be used (mean, median, min, max).,

- Parameters.ACTIVITY_PERCENTAGE
: the percentage of activities that shall be included in the two DFGs and the interleavings visualization.,

- Parameters.PATHS_PERCENTAG
: the percentage of paths that shall be included in the two DFGs and the interleavings visualization.,

- Parameters.DEPENDENCY_THRESHOLD
: the dependency threshold that shall be used to filter the edges of the DFG.,

- Parameters.MIN_FACT_EDGES_INTERLEAVINGS
: parameter that regulates the fraction of interleavings that is shown in the diagram.


## Creating an OCEL out of the Interleavings


Given two logs having related cases, we saw how to calculate the interleavings between the logs.
In this section, we want to exploit the information contained in the two logs and in their
interleavings to create an object-centric event log (OCEL). This will contain the events of the
two event logs and the connections between them. The OCEL can be used with any object-centric
process mining technique.
An example is reported on the right.


```python
import pandas as pd
import pm4py

if __name__ == "__main__":
	dataframe1 = pd.read_csv("tests/input_data/interleavings/receipt_even.csv")
	dataframe1 = pm4py.format_dataframe(dataframe1)
	dataframe2 = pd.read_csv("tests/input_data/interleavings/receipt_odd.csv")
	dataframe2 = pm4py.format_dataframe(dataframe2)
	case_relations = pd.read_csv("tests/input_data/interleavings/case_relations.csv")

	from pm4py.algo.discovery.ocel.interleavings import algorithm as interleavings_discovery
	interleavings = interleavings_discovery.apply(dataframe1, dataframe2, case_relations)

	from pm4py.objects.ocel.util import log_ocel
	ocel = log_ocel.from_interleavings(dataframe1, dataframe2, interleavings)
```




## Merging Related Logs (Case Relations)


If two event logs of two inter-related process are considered, it may make sense for some
analysis to merge them. The resulting log will contain cases which contain events of the first
and the second event log.
This happens when popular enterprise processes such as the P2P and the O2C are considered.
If a sales order is placed which require a material that is not available, a purchase order
can be operated to a supplier in order to get the material and fulfill the sales order.
For the merge operation, we will need to consider:,

- A 
reference
 event log (whose cases will be enriched by the events of the other event log.,

- An event log to be merged (its events end up in the cases of the reference event log).,

- A set of case relationships between them.
An example is reported on the right. The result is a traditional event log.


```python
import pandas as pd
import pm4py
from pm4py.algo.merging.case_relations import algorithm as case_relations_merging
import os

if __name__ == "__main__":
	dataframe1 = pd.read_csv(os.path.join("tests", "input_data", "interleavings", "receipt_even.csv"))
	dataframe1 = pm4py.format_dataframe(dataframe1)
	dataframe2 = pd.read_csv(os.path.join("tests", "input_data", "interleavings", "receipt_odd.csv"))
	dataframe2 = pm4py.format_dataframe(dataframe2)
	case_relations = pd.read_csv(os.path.join("tests", "input_data", "interleavings", "case_relations.csv"))
	merged = case_relations_merging.apply(dataframe1, dataframe2, case_relations)
```




## Network Analysis


The classical social network analysis methods (such as the ones described in this page at the later sections)
are based on the order of the events inside a case. For example, the Handover of Work metric considers
the directly-follows relationships between resources during the work of a case. An edge is added between
the two resources if such relationships occurs.
Real-life scenarios may be more complicated. At first, is difficult to collect events inside the same
case without having convergence/divergence issues (see first section of the OCEL part). At second,
the type of relationship may also be important. Consider for example the relationship between two resources:
this may be more efficient if the activity that is executed is liked by the resources, rather than
disgusted.
The 
network analysis
 that we introduce in this section generalizes some existing social network analysis
metrics, becoming independent from the choice of a case notion and permitting to build a multi-graph
instead of a simple graph.
With this, we assume events to be linked by signals. An event emits a signal (that is contained as one
attribute of the event) that is assumed to be received by other events (also, this is an attribute of these events)
that follow the first event in the log. So, we assume there is an 
OUT
 attribute (of the event) that is identical to the 
IN
 attribute (of the other events).
When we collect this information, we can build the network analysis graph:,

- The source node of the relation is given by an aggregation over a 
node_column_source
 attribute.,

- The target node of the relation is given by an aggregation over a 
node_column_target
 attribute.,

- The type of edge is given by an aggregation over an 
edge_column
 attribute.,

- The network analysis graph can either be annotated with frequency or performance information.
In the right, an example of network analysis, producing a multigraph annotated
with frequency information, and performing a visualization of the same, is reported.


```python
import os
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "receipt.xes"))

	frequency_edges = pm4py.discover_network_analysis(log, out_column="case:concept:name", in_column="case:concept:name", node_column_source="org:group", node_column_target="org:group", edge_column="concept:name", performance=False)
	pm4py.view_network_analysis(frequency_edges, variant="frequency", format="svg", edge_threshold=10)
```


In the previous example, we have loaded one traditional event log (the 
receipt.xes
event log), and performed the network analysis with the follows choice of parameters:,

- The OUT-column is set to 
case:concept:name
 and the IN-column is set also to

case:concept:name
 (that means, succeeding events of the same case are connected).,

- The 
node_column_source
 and 
node_column_target
 attribute are set to 
org:group
 (we want to see the network
of relations between different organizational groups.,

- The 
edge_column
 attribute is set to 
concept:name
 (we want to see the frequency/performance
of edges between groups, depending on the activity, so we can evaluate advantageous exchanges).
Note that in the previous case, we resorted to use the case identifier as OUT/IN column,
but that's just a specific example (the OUT and IN columns can be different, and differ from the
case identifier).
In the right, an example of network analysis, producing a multigraph annotated
with performance information, and performing a visualization of the same, is reported.


```python
import os
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "receipt.xes"))

	performance_edges = pm4py.discover_network_analysis(log, out_column="case:concept:name", in_column="case:concept:name", node_column_source="org:group", node_column_target="org:group", edge_column="concept:name", performance=True)
	pm4py.view_network_analysis(performance_edges, variant="performance", format="svg", edge_threshold=10)
```


The visualization supports the following parameters:,

- format
: the format of the visualization (default: png).,

- bgcolor
: the background color of the produced picture.,

- activity_threshold
: the minimum number of occurrences for an activity to be included (default: 1).,

- edge_threshold
: the minimum number of occurrences for an edge to be included (default: 1).


## Link Analysis


While the goal of the 
network analysis
 is to provide an aggregated visualization of the links between
different events, the goal of 
link analysis
 is just the discovery of the links between the events,
to be able to reason about them.
In the examples that follow, we are going to consider the document flow table 
VBFA
 of SAP.
This table contains some properties and the connections between sales orders documents (e.g. the order document
itself, the delivery documents, the invoice documents). Reasoning on the properties of the links could help
to understand anomalous situations (e.g. the currency/price is changed during the order's lifecycle).
A link analysis starts from the production of a 
link analysis dataframe
.
This contains the linked events according to the provided specification of the attributes.
First, we load a CSV containing the information from a 
VBFA
 table extracted
from an educational instance of SAP. Then, we do some pre-processing to ensure
the consistency of the data contained in the dataframe.
Then, we discover the 
link analysis dataframe
.


```python
import pandas as pd
from pm4py.algo.discovery.ocel.link_analysis import algorithm as link_analysis
import os

if __name__ == "__main__":
	dataframe = pd.read_csv(os.path.join("tests", "input_data", "ocel", "VBFA.zip"), compression="zip", dtype="str")
	dataframe["time:timestamp"] = dataframe["ERDAT"] + " " + dataframe["ERZET"]
	dataframe["time:timestamp"] = pd.to_datetime(dataframe["time:timestamp"], format="%Y%m%d %H%M%S")
	dataframe["RFWRT"] = dataframe["RFWRT"].astype(float)
	dataframe = link_analysis.apply(dataframe, parameters={"out_column": "VBELN", "in_column": "VBELV",
														   "sorting_column": "time:timestamp", "propagate": True})
```


At this point, several analysis could be performed.
For example, findings the interconnected documents for which
the currency differs between the two documents can be done as follows.


```python
if __name__ == "__main__":
	df_currency = dataframe[(dataframe["WAERS_out"] != " ") & (dataframe["WAERS_in"] != " ") & (
				dataframe["WAERS_out"] != dataframe["WAERS_in"])]
	print(df_currency[["WAERS_out", "WAERS_in"]].value_counts())
```


It is also possible to evaluate the amount of the documents, in order
to identify discrepancies.


```python
if __name__ == "__main__":
	df_amount = dataframe[(dataframe["RFWRT_out"] > 0) & (dataframe["RFWRT_out"] < dataframe["RFWRT_in"])]
	print(df_amount[["RFWRT_out", "RFWRT_in"]])
```


The parameters of the link analysis algorithm are:,

- Parameters.OUT_COLUMN
: the column of the dataframe that is used to link the 
source
 events to the target events.,

- Parameters.IN_COLUMN
: the column of the dataframe that is used to link the 
target
 events to the source events.,

- Parameters.SORTING_COLUMN
: the attribute which is used preliminarly to sort the dataframe.,

- Parameters.INDEX_COLUMN
: the name of the column of the dataframe that should be used to store the incremental event index.,

- Parameters.LOOK_FORWARD
: merge an event e1 with an event e2 (
e1.OUT = e2.IN
) only if the index in the dataframe
of e1 is lower than the index of the dataframe of e2.,

- Parameters.KEEP_FIRST_OCCURRENCE
 if several events e21, e22 are such that 
e1.OUT = e21.IN = e22.IN
,
keep only the relationship between 
e1
 and 
e21
.,

- Parameters.PROPAGATE
: propagate the discovered relationships. If e1, e2, e3 are such that 
e1.OUT = e2.IN
and 
e2.OUT = e3.IN
, then consider e1 to be in relationship also with e3.


## OC-DFG discovery


Object-centric directly-follows multigraphs
 are a composition of directly-follows
graphs for the single object type, which can be annotated with different metrics considering
the entities of an object-centric event log (i.e., events, unique objects, total objects).
We provide both the discovery of the OC-DFG (which provides a generic objects allowing for
many different choices of the metrics), and the visualization of the same.
An example, in which an object-centric event log is loaded,
an object-centric directly-follows multigraph is discovered,
and visualized with frequency annotation on the screen, is provided on the right.


```python
import pm4py
import os

if __name__ == "__main__":
	ocel = pm4py.read_ocel(os.path.join("tests", "input_data", "ocel", "example_log.jsonocel"))
	ocdfg = pm4py.discover_ocdfg(ocel)
	# views the model with the frequency annotation
	pm4py.view_ocdfg(ocdfg, format="svg")
```


An example, in which an object-centric event log is loaded,
an object-centric directly-follows multigraph is discovered,
and visualized with performance annotation on the screen, is provided on the right.


```python
import pm4py
import os

if __name__ == "__main__":
	ocel = pm4py.read_ocel(os.path.join("tests", "input_data", "ocel", "example_log.jsonocel"))
	ocdfg = pm4py.discover_ocdfg(ocel)
	# views the model with the performance annotation
	pm4py.view_ocdfg(ocdfg, format="svg", annotation="performance", performance_aggregation="median")
```


The visualization supports the following parameters:,

- annotation
: The annotation to use for the visualization. Values: frequency (the frequency annotation), performance (the performance annotation).,

- act_metric
: The metric to use for the activities. Available values: events (number of events), unique_objects (number of unique objects), total_objects (number of total objects).,

- edge_metric
: The metric to use for the edges. Available values: event_couples (number of event couples), unique_objects (number of unique objects), total_objects (number of total objects).,

- act_threshold
: The threshold to apply on the activities frequency (default: 0). Only activities having a frequency >= than this are kept in the graph.,

- edge_threshold
: The threshold to apply on the edges frequency (default 0). Only edges having a frequency >= than this are kept in the graph. ,

- performance_aggregation
: The aggregation measure to use for the performance: mean, median, min, max, sum,

- format
: The format of the output visualization (default: png)


## OC-PN discovery


Object-centric Petri Nets
 (OC-PN) are formal models, discovered on top of the object-centric event logs,
using an underlying process discovery algorithm (such as the Inductive Miner). They have been described in the scientific
paper:
van der Aalst, Wil MP, and Alessandro Berti. "Discovering object-centric Petri nets." Fundamenta informaticae 175.1-4 (2020): 1-40.
In pm4py, we offer a basic implementation of object-centric Petri nets (without any additional decoration).
An example, in which an object-centric event log is loaded, the discovery algorithm is applied,
and the OC-PN is visualized, is reported on the right.


```python
import pm4py
import os

if __name__ == "__main__":
	ocel = pm4py.read_ocel(os.path.join("tests", "input_data", "ocel", "example_log.jsonocel"))
	model = pm4py.discover_oc_petri_net(ocel)
	pm4py.view_ocpn(model, format="svg")
```




## Object Graphs on OCEL


It is possible to catch the interaction between the different objects of an OCEL
in different ways. In pm4py, we offer support for the computation of some object-based graphs:,

- The 
objects interaction
 graph connects two objects if they are related in some
event of the log.,

- The 
objects descendants
 graph connects an object, which is related to an event
but does not start its lifecycle with the given event, to all the objects that start their
lifecycle with the given event.,

- The 
objects inheritance
 graph connects an object, which terminates its
lifecycle with the given event, to all the objects that start their lifecycle with the
given event.,

- The 
objects cobirth
 graph connects objects which start their lifecycle within
the same event.,

- The 
objects codeath
 graph connects objects which complete their lifecycle
within the same event.
The 
object interactions graph
 can be computed as follows:


```python
import pm4py

if __name__ == "__main__":
	ocel = pm4py.read_ocel("tests/input_data/ocel/example_log.jsonocel")
	from pm4py.algo.transformation.ocel.graphs import object_interaction_graph
	graph = object_interaction_graph.apply(ocel)
```


The 
object descendants graph
 can be computed as follows:


```python
import pm4py

if __name__ == "__main__":
	ocel = pm4py.read_ocel("tests/input_data/ocel/example_log.jsonocel")
	from pm4py.algo.transformation.ocel.graphs import object_descendants_graph
	graph = object_descendants_graph.apply(ocel)
```


The 
object inheritance graph
 can be computed as follows:


```python
import pm4py

if __name__ == "__main__":
	ocel = pm4py.read_ocel("tests/input_data/ocel/example_log.jsonocel")
	from pm4py.algo.transformation.ocel.graphs import object_inheritance_graph
	graph = object_inheritance_graph.apply(ocel)
```


The 
object cobirth graph
 can be computed as follows:


```python
import pm4py

if __name__ == "__main__":
	ocel = pm4py.read_ocel("tests/input_data/ocel/example_log.jsonocel")
	from pm4py.algo.transformation.ocel.graphs import object_cobirth_graph
	graph = object_cobirth_graph.apply(ocel)
```


The 
object codeath graph
 can be computed as follows:


```python
import pm4py

if __name__ == "__main__":
	ocel = pm4py.read_ocel("tests/input_data/ocel/example_log.jsonocel")
	from pm4py.algo.transformation.ocel.graphs import object_codeath_graph
	graph = object_codeath_graph.apply(ocel)
```




## Feature Extraction on OCEL - Object-Based


For machine learning purposes, we might want to create a feature matrix, which
contains a row for every object of the object-centric event log.
The dimensions which can be considered for the computation of features are different:,

- The 
lifecycle
 of an object (sequence of events in the log which are related
to an object). From this dimension, several features, including the length of the lifecycle,
the duration of the lifecycle, can be computed. Moreover, the sequence of the activities
inside the lifecycle can be computed. For example, the one-hot encoding of the
activities can be considered (every activity is associated to a different column,
and the number of events of the lifecycle having the given activity is reported).,

- Features extracted from the graphs computed on the OCEL (objects interaction graph,
objects descendants graph, objects inheritance graph, objects cobirth/codeath graph).
For every one of these, the number of objects connected to a given object are considered
as feature.,

- The number of objects having a lifecycle intersecting (on the time dimension)
with the current object.,

- The one-hot-encoding of a specified collection of string attributes.,

- The encoding of the values of a specified collection of numeric attributes.
To compute the object-based features, the following command can be used
(we would like to consider 
oattr1
 as the only string attribute to one-hot-encode,
and 
oattr2
 as the only numeric attribute to encode). If no string/numeric attributes
should be included, the parameters can be omitted.


```python
import pm4py

if __name__ == "__main__":
	ocel = pm4py.read_ocel("tests/input_data/ocel/example_log.jsonocel")
	from pm4py.algo.transformation.ocel.features.objects import algorithm
	data, feature_names = algorithm.apply(ocel,
										parameters={"str_obj_attr": ["oattr1"], "num_obj_attr": ["oattr2"]})
```




## Feature Extraction on OCEL - Event-Based


For machine learning purposes, we might want to create a feature matrix, which
contains a row for every event of the object-centric event log.
The dimensions which can be considered for the computation of features are different:,

- The timestamp of the event. This can be encoded in different way (absolute timestamp,
hour of the day, day of the week, month).,

- The activity of the event. An one-hot encoding of the activity values can be performed.,

- The related objects to the event. Features such as the total number of related objects,
the number of related objects per type, the number of objects which start their lifecycle
with the current event, the number of objects which complete their lifecycle with the
current event) can be considered.,

- The one-hot-encoding of a specified collection of string attributes.,

- The encoding of the values of a specified collection of numeric attributes.
To compute the event-based features, the following command can be used
(we would like to consider 
prova
 as the only string attribute to one-hot-encode,
and 
prova2
 as the only numeric attribute to encode). If no string/numeric attributes
should be included, the parameters can be omitted.


```python
import pm4py

if __name__ == "__main__":
	ocel = pm4py.read_ocel("tests/input_data/ocel/example_log.jsonocel")
	from pm4py.algo.transformation.ocel.features.events import algorithm
	data, feature_names = algorithm.apply(ocel,
										parameters={"str_obj_attr": ["prova"], "num_obj_attr": ["prova2"]})
```




## OCEL validation


The validation process permits to recognise valid JSON-OCEL/XML-OCEL files before
starting the parsing. This is done against a schema which contains the basic structure
that should be followed by JSON-OCEL and XML-OCEL files.
The validation of a JSON-OCEL file is done as follows:


```python
from pm4py.objects.ocel.validation import jsonocel

if __name__ == "__main__":
	validation_result = jsonocel.apply("tests/input_data/ocel/example_log.jsonocel", "tests/input_data/ocel/schema.json")
	print(validation_result)
```


The validation of a XML-OCEL file is done as follows:


```python
from pm4py.objects.ocel.validation import xmlocel

if __name__ == "__main__":
	validation_result = xmlocel.apply("tests/input_data/ocel/example_log.xmlocel", "tests/input_data/ocel/schema.xml")
	print(validation_result)
```


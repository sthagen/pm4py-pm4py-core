Supported/Described Version(s): pm4py 2.7.11.11
 
This documentation assumes that the reader has a basic understanding of process
mining
and python concepts.


# Handling Event Data




## Importing IEEE XES files


IEEE XES is a standard format describing how event logs are stored.
For more information about the format, please study the 
IEEE XES Website (http://www.xes-standard.org)
.
A simple synthetic event log (
running-example.xes
) can be downloaded from 
here (static/assets/examples/running-example.xes)
.
Note that several real event logs have been made available, over the past few
years.
You can find them 
here (https://data.4tu.nl/search?q=:keyword:%20real%20life%20event%20logs)
.

 
 
The example code on the right shows how to import an event log, stored in the IEEE
XES format, given a file path to the log file.
The code fragment uses the standard importer (iterparse, described in a later
paragraph).
Note that IEEE XES Event Logs are imported into a Pandas dataframe object.


```python
import pm4py
if __name__ == "__main__":
	log = pm4py.read_xes('tests/input_data/running-example.xes')
```




## Importing CSV files


Apart from the IEEE XES standard, a lot of event logs are actually stored in a 
CSV
file (https://en.wikipedia.org/wiki/Comma-separated_values)
.
In general, there is two ways to deal with CSV files in pm4py:
,

- Import the CSV into a 
pandas (https://pandas.pydata.org)
 
DataFrame (https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_csv.html#pandas.read_csv)
;
In general, most existing algorithms in pm4py are coded to be flexible in terms
of their
input, i.e., if a certain event log object is provided that is not in the right
form, we
translate it to the appropriate form for you.
Hence, after importing a dataframe, most algorithms are directly able to work
with the
data frame.
,

- Convert the CSV into an event log object (similar to the result of the IEEE XES
importer
presented in the previous section);
In this case, the first step is to import the CSV file using pandas (similar to
the
previous bullet) and subsequently converting it to the event log object.
In the remainder of this section, we briefly highlight how to convert a pandas
DataFrame
to an event log.
Note that most algorithms use the same type of conversion, in case a given
event data
object is not of the right type.
 
 
The example code on the right shows how to convert a CSV file into the pm4py
internal event data object types.
By default, the converter converts the dataframe to an Event Log object (i.e., not
an Event Stream).


```python
import pandas as pd
import pm4py

if __name__ == "__main__":
	dataframe = pd.read_csv('tests/input_data/running-example.csv', sep=',')
	dataframe = pm4py.format_dataframe(dataframe, case_id='case:concept:name', activity_key='concept:name', timestamp_key='time:timestamp')
	event_log = pm4py.convert_to_event_log(dataframe)
```


Note that the example code above does not directly work in a lot of cases. Let us consider a very simple example event log, and, assume it is stored
as a 
`csv`,

-file:



|CaseID|Activity|Timestamp|clientID|
|---|---|---|---|
|1|register request|20200422T0455|1337|
|2|register request|20200422T0457|1479|
|1|submit payment|20200422T0503|1337|
|||||



In this small example table, we observe four columns, i.e., 
`CaseID`
,
`Activity`
,
`Timestamp`
 and 
`clientID`
.
Clearly, when importing the data and converting it to an Event Log object, we aim to
combine all rows (events) with the same value for the 
`CaseID`
 column
together.
Another interesting phenomenon in the example data is the fourth column, i.e.,
`clientID`
.
In fact, the client ID is an attribute that will not change over the course of
execution
a process instance, i.e., it is a 
case-level attribute
.
pm4py allows us to specify that a column actually describes a case-level attribute
(under the assumption that the attribute does not change during the execution of a
process).

The example code on the right shows how to convert the previously examplified csv
data file.
After loading the csv file of the example table, we rename the 
`clientID`
column to 
`case:clientID`
 (this is a specific operation provided by
pandas!).



```python
import pandas as pd
import pm4py

if __name__ == "__main__":
	dataframe = pd.read_csv('tests/input_data/running-example-transformed.csv', sep=',')
	dataframe = dataframe.rename(columns={'clientID': 'case:clientID'})
	dataframe = pm4py.format_dataframe(dataframe, case_id='CaseID', activity_key='Activity', timestamp_key='Timestamp')
	event_log = pm4py.convert_to_event_log(dataframe)
```




## Converting Event Data


In this section, we describe how to convert event log objects from one object type
to another object type.
There are three objects, which we are able to 'switch' between, i.e., Event Log,
Event Stream and Data Frame objects.
Please refer to the previous code snippet for an example of applying log conversion
(applied when importing a CSV object).
Finally, note that most algorithms internally use the converters, in order to be
able to handle an input event data object of any form.
In such a case, the default parameters are used.
To convert from any object to an event log, the following method can be used:


```python
import pm4py
if __name__ == "__main__":
	event_log = pm4py.convert_to_event_log(dataframe)
```


To convert from any object to an event stream, the following method can be used:


```python
import pm4py
if __name__ == "__main__":
	event_stream = pm4py.convert_to_event_stream(dataframe)
```


To convert from any object to a dataframe, the following method can be used:


```python
import pm4py
if __name__ == "__main__":
	dataframe = pm4py.convert_to_dataframe(dataframe)
```




## Exporting IEEE XES files


Exporting an Event Log object to an IEEE Xes file is fairly straightforward in pm4py.
Consider the example code fragment on the right, which depicts this
functionality.


```python
import pm4py
if __name__ == "__main__":
	pm4py.write_xes(log, 'exported.xes')
```


In the example, the 
`log`
 object is assumed to be an Event Log object.
The exporter also accepts an Event Stream or DataFrame object as an input.
However, the exporter will first convert the given input object into an Event Log.
Hence, in this case, standard parameters for the conversion are used.
Thus, if the user wants more control, it is advisable to apply the conversion to
Event Log, prior to exporting.



## Exporting logs to CSV


To export an event log to a 
`csv`,

-file, pm4py uses Pandas.
Hence, an event log is first converted to a Pandas Data Frame, after which it is
written to disk.



```python
import pandas as pd
import pm4py

if __name__ == "__main__":
	dataframe = pm4py.convert_to_dataframe(log)
	dataframe.to_csv('exported.csv')
```


 
In case an event log object is provided that is not a dataframe, i.e., an Event Log
or Event Stream, the conversion is applied, using the default parameter values,
i.e., as presented in the 
Converting
Event Data (#item-convert-logs)
 section.
Note that exporting event data to as csv file has no parameters.
In case more control over the conversion is needed, please apply a conversion to
dataframe first, prior to exporting to csv.



## I/O with Other File Types


At this moment, I/O of any format supported by Pandas (dataframes) is implicitly
supported.
As long as data can be loaded into a Pandas dataframe, pm4py is reasonably able to work
with such files.
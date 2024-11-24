# Handling Event Data

## Importing IEEE XES Files

IEEE XES is a standard format describing how event logs are stored.  
For more information about the format, please study the [IEEE XES Website](http://www.xes-standard.org).  
A simple synthetic event log (`running-example.xes`) can be downloaded from [here](static/assets/examples/running-example.xes).  
Note that several real event logs have been made available over the past few years.  
You can find them [here](https://data.4tu.nl/search?q=:keyword:%20real%20life%20event%20logs).

The example code on the right shows how to import an event log stored in the IEEE XES format, given a file path to the log file.  
The code fragment uses the standard importer (`iterparse`, described in a later paragraph).  
Note that IEEE XES Event Logs are imported into a Pandas DataFrame object.

```python
import pm4py
if __name__ == "__main__":
    log = pm4py.read_xes('tests/input_data/running-example.xes')
```

## Importing CSV Files

Apart from the IEEE XES standard, many event logs are actually stored in a [CSV](https://en.wikipedia.org/wiki/Comma-separated_values) file.

In general, there are two ways to deal with CSV files in PM4Py:

- **Import the CSV into a [Pandas](https://pandas.pydata.org) [DataFrame](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_csv.html#pandas.read_csv);**  
  In general, most existing algorithms in PM4Py are coded to be flexible in terms of their input.  
  If a certain event log object is provided that is not in the right form, we translate it to the appropriate form for you.  
  Hence, after importing a DataFrame, most algorithms are directly able to work with the DataFrame.

- **Convert the CSV into an event log object** (similar to the result of the IEEE XES importer presented in the previous section);  
  In this case, the first step is to import the CSV file using Pandas (similar to the previous bullet) and subsequently convert it to the event log object.  
  In the remainder of this section, we briefly highlight how to convert a Pandas DataFrame to an event log.  
  Note that most algorithms use the same type of conversion in case a given event data object is not of the right type.

The example code on the right shows how to convert a CSV file into the PM4Py internal event data object types.  
By default, the converter converts the DataFrame to an Event Log object (i.e., not an Event Stream).

```python
import pandas as pd
import pm4py

if __name__ == "__main__":
    dataframe = pd.read_csv('tests/input_data/running-example.csv', sep=',')
    dataframe = pm4py.format_dataframe(dataframe, case_id='case:concept:name', activity_key='concept:name', timestamp_key='time:timestamp')
    event_log = pm4py.convert_to_event_log(dataframe)
```

Note that the example code above does not directly work in many cases. Let us consider a very simple example event log and assume it is stored as a `csv` file:

| CaseID | Activity         | Timestamp    | clientID |
|--------|------------------|--------------|----------|
| 1      | register request | 20200422T0455 | 1337     |
| 2      | register request | 20200422T0457 | 1479     |
| 1      | submit payment   | 20200422T0503 | 1337     |
|        |                  |              |          |

In this small example table, we observe four columns: `CaseID`, `Activity`, `Timestamp`, and `clientID`.  
Clearly, when importing the data and converting it to an Event Log object, we aim to combine all rows (events) with the same value for the `CaseID` column together.  
Another interesting phenomenon in the example data is the fourth column, `clientID`.  
In fact, the client ID is an attribute that will not change over the course of executing a process instance; i.e., it is a case-level attribute.  
PM4Py allows us to specify that a column actually describes a case-level attribute (under the assumption that the attribute does not change during the execution of a process).

The example code on the right shows how to convert the previously exemplified CSV data file.  
After loading the CSV file of the example table, we rename the `clientID` column to `case:clientID` (this is a specific operation provided by Pandas!).

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

In this section, we describe how to convert event log objects from one object type to another.  
There are three objects that we can switch between: Event Log, Event Stream, and DataFrame objects.  
Please refer to the previous code snippet for an example of applying log conversion (applied when importing a CSV object).  
Finally, note that most algorithms internally use the converters to handle an input event data object of any form.  
In such cases, the default parameters are used.

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

To convert from any object to a DataFrame, the following method can be used:

```python
import pm4py
if __name__ == "__main__":
    dataframe = pm4py.convert_to_dataframe(dataframe)
```

## Exporting IEEE XES Files

Exporting an Event Log object to an IEEE XES file is straightforward in PM4Py.  
Consider the example code fragment on the right, which depicts this functionality.

```python
import pm4py
if __name__ == "__main__":
    pm4py.write_xes(log, 'exported.xes')
```

In the example, the `log` object is assumed to be an Event Log object.  
The exporter also accepts an Event Stream or DataFrame object as input.  
However, the exporter will first convert the given input object into an Event Log.  
Hence, in this case, standard parameters for the conversion are used.  
Thus, if the user wants more control, it is advisable to apply the conversion to an Event Log prior to exporting.

## Exporting Logs to CSV

To export an event log to a `csv` file, PM4Py uses Pandas.  
Hence, an event log is first converted to a Pandas DataFrame, after which it is written to disk.

```python
import pandas as pd
import pm4py

if __name__ == "__main__":
    dataframe = pm4py.convert_to_dataframe(log)
    dataframe.to_csv('exported.csv')
```

In case an event log object is provided that is not a DataFrame, i.e., an Event Log or Event Stream, the conversion is applied using the default parameter values, as presented in the [Converting Event Data](#converting-event-data) section.  
Note that exporting event data as a CSV file has no parameters.  
If more control over the conversion is needed, please apply a conversion to a DataFrame first prior to exporting to CSV.

## I/O with Other File Types

At this moment, I/O of any format supported by Pandas (DataFrames) is implicitly supported.  
As long as data can be loaded into a Pandas DataFrame, PM4Py is reasonably able to work with such files.

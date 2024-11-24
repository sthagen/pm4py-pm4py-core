# Feature Selection

An operation of feature selection allows representing the event log in a tabular format. This is important for operations such as prediction and anomaly detection.

## Automatic Feature Selection

In PM4Py, we offer ways to perform automatic feature selection. As an example, let us import the receipt log and perform automatic feature selection on top of it. First, we import the receipt log:

```python
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes("tests/input_data/receipt.xes")
	log = pm4py.convert_to_event_log(log)
```

Then, let’s perform the automatic feature selection:

```python
from pm4py.algo.transformation.log_to_features import algorithm as log_to_features

if __name__ == "__main__":
	data, feature_names = log_to_features.apply(log)
	print(feature_names)
```

Printing the value `feature_names`, we see that the following attributes were selected:

- The attribute `channel` at the trace level (this assumes values Desk, Intern, Internet, Post, e-mail).

- The attribute `department` at the trace level (this assumes values Customer contact, Experts, General).

- The attribute `group` at the event level (this assumes values EMPTY, Group 1, Group 12, Group 13, Group 14, Group 15, Group 2, Group 3, Group 4, Group 7).

No numeric attribute value is selected. If we print `feature_names`, we get the following representation:
[`trace:channel@Desk`, `trace:channel@Intern`, `trace:channel@Internet`, `trace:channel@Post`, `trace:channel@e-mail`, `trace:department@Customer contact`, `trace:department@Experts`, `trace:department@General`, `event:org:group@EMPTY`, `event:org:group@Group 1`, `event:org:group@Group 12`, `event:org:group@Group 13`, `event:org:group@Group 14`, `event:org:group@Group 15`, `event:org:group@Group 2`, `event:org:group@Group 3`, `event:org:group@Group 4`, `event:org:group@Group 7`]
So, we see that we have different features for different values of the attribute. This is called one-hot encoding. Actually, a case is assigned to 0 if it does not contain an event with the given value for the attribute; a case is assigned to 1 if it contains at least one event with the attribute.

If we represent the features as a dataframe:

```python
import pandas as pd
if __name__ == "__main__":
	df = pd.DataFrame(data, columns=feature_names)
	print(df)
```

We can see the features assigned to each different case.

## Manual Feature Selection

Manual feature selection allows specifying which attributes should be included in the feature selection. These may include, for example:

- The activities performed in the process execution (usually contained in the event attribute `concept:name`).

- The resources that perform the process execution (usually contained in the event attribute `org:resource`).

- Some numeric attributes, at the discretion of the user.

To do so, we have to call the method `log_to_features.apply`. The types of features that can be considered by manual feature selection are:

| Parameter           | Description                                                                                                                                                                  |
|---------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `str_ev_attr`       | String attributes at the event level: these are one-hot encoded into features that may assume value 0 or value 1.                                                              |
| `str_tr_attr`       | String attributes at the trace level: these are one-hot encoded into features that may assume value 0 or value 1.                                                              |
| `num_ev_attr`       | Numeric attributes at the event level: these are encoded by including the last value of the attribute among the events of the trace.                                           |
| `num_tr_attr`       | Numeric attributes at the trace level: these are encoded by including the numerical value.                                                                                     |
| `str_evsucc_attr`   | Successions related to the string attributes values at the event level: for example, if we have a trace [A,B,C], it might be important to include not only the presence of the single values A, B, and C as features, but also the presence of the directly-follows couples (A,B) and (B,C). |

Let’s consider, for example, a feature selection where we are interested in:

- Whether a process execution contains an activity.

- Whether a process execution contains a resource.

- Whether a process execution contains a directly-follows path between different activities.

- Whether a process execution contains a directly-follows path between different resources.

We see that the number of features is significantly larger in this setting.

```python
from pm4py.algo.transformation.log_to_features import algorithm as log_to_features

if __name__ == "__main__":
	data, feature_names = log_to_features.apply(log, parameters={"str_ev_attr": ["concept:name", "org:resource"], "str_tr_attr": [], "num_ev_attr": [], "num_tr_attr": [], "str_evsucc_attr": ["concept:name", "org:resource"]})
	print(len(feature_names))
```

## Calculating Useful Features

Other features include the cycle and the lead time associated with a case. Here, we may assume to have:

- A log with lifecycles, where each event is instantaneous,

- OR an interval log, where events may be associated with two timestamps (start and end timestamp).

The lead/cycle time can be calculated on top of interval logs. If we have a lifecycle log, we need to convert it with:

```python
from pm4py.objects.log.util import interval_lifecycle
if __name__ == "__main__":
	log = interval_lifecycle.to_interval(log)
```

Then, features such as the lead/cycle time can be inserted through the instructions:

```python
from pm4py.objects.log.util import interval_lifecycle
from pm4py.util import constants

if __name__ == "__main__":
	log = interval_lifecycle.assign_lead_cycle_time(log, parameters={
		constants.PARAMETER_CONSTANT_START_TIMESTAMP_KEY: "start_timestamp",
		constants.PARAMETER_CONSTANT_TIMESTAMP_KEY: "time:timestamp"})
```

After the provision of the start timestamp attribute (in this case, `start_timestamp`) and the timestamp attribute (in this case, `time:timestamp`), the following features are returned by the method:

- `@@approx_bh_partial_cycle_time` => incremental cycle time associated with the event (the cycle time of the last event is the cycle time of the instance).

- `@@approx_bh_partial_lead_time` => incremental lead time associated with the event.

- `@@approx_bh_overall_wasted_time` => difference between the partial lead time and the partial cycle time values.

- `@@approx_bh_this_wasted_time` => wasted time ONLY with regards to the activity described by the ‘interval’ event.

- `@@approx_bh_ratio_cycle_lead_time` => measures the incremental Flow Rate (between 0 and 1).

These are all numerical attributes; hence, we can refine the feature extraction by doing:

```python
from pm4py.algo.transformation.log_to_features import algorithm as log_to_features

if __name__ == "__main__":
	data, feature_names = log_to_features.apply(log, parameters={"str_ev_attr": ["concept:name", "org:resource"], "str_tr_attr": [], "num_ev_attr": ["@@approx_bh_partial_cycle_time", "@@approx_bh_partial_lead_time", "@@approx_bh_overall_wasted_time", "@@approx_bh_this_wasted_time", "@approx_bh_ratio_cycle_lead_time"], "num_tr_attr": [], "str_evsucc_attr": ["concept:name", "org:resource"]})
```

We also provide the calculation of additional intra/inter case features, which can be enabled as additional boolean parameters of the `log_to_features.apply` method. These include:

- `ENABLE_CASE_DURATION`: enables the case duration as an additional feature.

- `ENABLE_TIMES_FROM_FIRST_OCCURRENCE`: enables the addition of the times from the start of the case to the end of the case, from the first occurrence of an activity of a case.

- `ENABLE_TIMES_FROM_LAST_OCCURRENCE`: enables the addition of the times from the start of the case to the end of the case, from the last occurrence of an activity of a case.

- `ENABLE_DIRECT_PATHS_TIMES_LAST_OCC`: adds the duration of the last occurrence of a directed (i, i+1) path in the case as a feature.

- `ENABLE_INDIRECT_PATHS_TIMES_LAST_OCC`: adds the duration of the last occurrence of an indirect (i, j) path in the case as a feature.

- `ENABLE_WORK_IN_PROGRESS`: enables the work in progress (number of concurrent cases) as a feature.

- `ENABLE_RESOURCE_WORKLOAD`: enables the resource workload as a feature.

## PCA – Reducing the Number of Features

Some techniques (such as clustering, prediction, anomaly detection) suffer if the dimensionality of the dataset is too high. Hence, a dimensionality reduction technique (like PCA) helps to cope with the complexity of the data. Having a Pandas dataframe out of the features extracted from the log:

```python
import pandas as pd

if __name__ == "__main__":
	df = pd.DataFrame(data, columns=feature_names)
```

It is possible to reduce the number of features using techniques like PCA. Let’s create the PCA with a number of components equal to 5 and apply the PCA to the dataframe.

```python
from sklearn.decomposition import PCA

if __name__ == "__main__":
	pca = PCA(n_components=5)
	df2 = pd.DataFrame(pca.fit_transform(df))
```

So, from more than 400 columns, we reduce to 5 columns that contain most of the variance.

## Anomaly Detection

In this section, we consider the calculation of an anomaly score for the different cases. This is based on the features extracted and works better when a dimensionality reduction technique (such as PCA in the previous section) is applied. Let’s apply a method called `IsolationForest` to the dataframe. This permits adding a column `scores` that is lower than or equal to 0 when the case needs to be considered anomalous and greater than 0 when the case does not need to be considered anomalous.

```python
from sklearn.ensemble import IsolationForest
if __name__ == "__main__":
	model = IsolationForest()
	model.fit(df2)
	df2["scores"] = model.decision_function(df2)
```

To see which cases are more anomalous, we can sort the dataframe by inserting an index. Then, the print will show which cases are more anomalous:

```python
if __name__ == "__main__":
	df2["@@index"] = df2.index
	df2 = df2[["scores", "@@index"]]
	df2 = df2.sort_values("scores")
	print(df2)
```

## Evolution of the Features

We may be interested in evaluating the evolution of the features over time to identify positions in the event log with behavior that is different from the mainstream behavior. In PM4Py, we provide a method to graph the evolution of features over time. This can be done as in the following example:

```python
import os
import pm4py
from pm4py.algo.transformation.log_to_features.util import locally_linear_embedding
from pm4py.visualization.graphs import visualizer

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "receipt.xes"))
	x, y = locally_linear_embedding.apply(log)
	gviz = visualizer.apply(x, y, variant=visualizer.Variants.DATES,
							parameters={"title": "Locally Linear Embedding", "format": "svg", "y_axis": "Intensity"})
	visualizer.view(gviz)
```

## Event-based Feature Extraction

Some machine learning methods (for example, LSTM-based deep learning) do not require a specification of the features at the case level (where every case is transformed into a single vector of numerical features) but require a specification of a numerical row for each event of the case, containing the features of the given event. We can perform a default extraction of event-based features. In this case, the features to be extracted are extracted automatically.

```python
from pm4py.algo.transformation.log_to_features import algorithm as log_to_features

if __name__ == "__main__":
	data, features = log_to_features.apply(log, variant=log_to_features.Variants.EVENT_BASED)
```

We can also manually specify the set of features to be extracted. The names of the parameters (`str_ev_attr` and `num_ev_attr`) are equivalent to the explanations provided in the previous sections.

```python
from pm4py.algo.transformation.log_to_features import algorithm as log_to_features

if __name__ == "__main__":
	data, features = log_to_features.apply(log, variant=log_to_features.Variants.EVENT_BASED, parameters={"str_ev_attr": ["concept:name"], "num_ev_attr": []})
```

## Decision Tree About the Ending Activity of a Process

Decision trees are tools that help understand the conditions leading to a particular outcome. In this section, several examples related to the construction of decision trees are provided. Ideas behind building decision trees are presented in the scientific paper: de Leoni, Massimiliano, Wil MP van der Aalst, and Marcus Dees. "A general process mining framework for correlating, predicting and clustering dynamic behavior based on event logs."

The general scheme is as follows:

- A representation of the log, based on a given set of features, is obtained (for example, using one-hot encoding on string attributes and keeping numeric attributes as they are).

- A representation of the target classes is constructed.

- The decision tree is built.

- The decision tree is visualized.

A process instance may potentially finish with different activities, signaling different outcomes of the process instance. A decision tree may help understand the reasons behind each outcome. First, a log is loaded. Then, a representation of the log based on a given set of features is obtained.

```python
import os
import pm4py
log = pm4py.read_xes(os.path.join("tests", "input_data", "roadtraffic50traces.xes"))
log = pm4py.convert_to_event_log(log)

from pm4py.algo.transformation.log_to_features import algorithm as log_to_features

if __name__ == "__main__":
	data, feature_names = log_to_features.apply(log, parameters={"str_tr_attr": [], "str_ev_attr": ["concept:name"], "num_tr_attr": [], "num_ev_attr": ["amount"]})
```

Or an automatic representation (automatic selection of the attributes) could be obtained:

```python
data, feature_names = log_to_features.apply(log)
```

(Optional) The features that are extracted by these methods can be represented as a Pandas dataframe:

```python
import pandas as pd
if __name__ == "__main__":
	dataframe = pd.DataFrame(data, columns=feature_names)
```

(Optional) The dataframe can then be exported as a CSV file.

```python
if __name__ == "__main__":
	dataframe.to_csv("features.csv", index=False)
```

Then, the target classes are formed. Each endpoint of the process belongs to a different class.

```python
from pm4py.objects.log.util import get_class_representation
if __name__ == "__main__":
	target, classes = get_class_representation.get_class_representation_by_str_ev_attr_value_value(log, "concept:name")
```

The decision tree is then built and visualized.

```python
from sklearn import tree
if __name__ == "__main__":
	clf = tree.DecisionTreeClassifier()
	clf.fit(data, target)

	from pm4py.visualization.decisiontree import visualizer as dectree_visualizer
	gviz = dectree_visualizer.apply(clf, feature_names, classes)
```

## Decision Tree About the Duration of a Case (Root Cause Analysis)

A decision tree about the duration of a case helps understand the reasons behind a high case duration (or, at least, a case duration that is above the threshold). First, a log is loaded. A representation of the log based on a given set of features is obtained.

```python
import os
import pm4py
if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "roadtraffic50traces.xes"))

	from pm4py.algo.transformation.log_to_features import algorithm as log_to_features

	data, feature_names = log_to_features.apply(log, parameters={"str_tr_attr": [], "str_ev_attr": ["concept:name"], "num_tr_attr": [], "num_ev_attr": ["amount"]})
```

Or an automatic representation (automatic selection of the attributes) could be obtained:

```python
data, feature_names = log_to_features.apply(log)
```

Then, the target classes are formed. There are two classes: first, traces that are below the specified threshold (here, 200 days). Note that the time is given in seconds. Second, traces that are above the specified threshold.

```python
from pm4py.objects.log.util import get_class_representation
if __name__ == "__main__":
	target, classes = get_class_representation.get_class_representation_by_trace_duration(log, 2 * 8640000)
```

The decision tree is then built and visualized.

```python
from sklearn import tree
if __name__ == "__main__":
	clf = tree.DecisionTreeClassifier()
	clf.fit(data, target)

	from pm4py.visualization.decisiontree import visualizer as dectree_visualizer
	gviz = dectree_visualizer.apply(clf, feature_names, classes)
```

## Decision Mining

Decision mining allows, given:

- An event log,

- A process model (an accepting Petri net),

- A decision point,

to retrieve the features of the cases that take different directions. This permits, for example, to calculate a decision tree that explains the decisions.

Let’s start by importing a XES log:

```python
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes("tests/input_data/running-example.xes")
```

Calculating a model using the inductive miner:

```python
if __name__ == "__main__":
	net, im, fm = pm4py.discover_petri_net_inductive(log)
```

A visualization of the model can be obtained in the following way:

```python
from pm4py.visualization.petri_net import visualizer

if __name__ == "__main__":
	gviz = visualizer.apply(net, im, fm, parameters={visualizer.Variants.WO_DECORATION.value.Parameters.DEBUG: True})
	visualizer.view(gviz)
```

For this example, we choose the decision point `p_10`. There, a decision is made between the activities `examine casually` and `examine thoroughly`. To execute the decision mining algorithm, once we have a log, model, and a decision point, the following code can be used:

```python
from pm4py.algo.decision_mining import algorithm as decision_mining

if __name__ == "__main__":
	X, y, class_names = decision_mining.apply(log, net, im, fm, decision_point="p_10")
```

As we see, the outputs of the `apply` method are:

- `X`: a Pandas dataframe containing the features associated with the cases leading to a decision.

- `y`: a Pandas dataframe, a single column, containing the class number that is the output of the decision (in this case, the possible values are 0 and 1, since we have two target classes).

- `class_names`: the names of the output classes of the decision (in this case, `examine casually` and `examine thoroughly`).

These outputs can be used in a generic way with any classification or comparison technique. In particular, decision trees can be useful. We provide a function to automate the discovery of decision trees from the decision mining technique. The code to be applied is as follows:

```python
from pm4py.algo.decision_mining import algorithm as decision_mining

if __name__ == "__main__":
	clf, feature_names, classes = decision_mining.get_decision_tree(log, net, im, fm, decision_point="p_10")
```

Then, a visualization of the decision tree can be obtained as follows:

```python
from pm4py.visualization.decisiontree import visualizer as tree_visualizer

if __name__ == "__main__":
	gviz = tree_visualizer.apply(clf, feature_names, classes)
```

## Feature Extraction on Dataframes

While the feature extraction described in the previous sections is generic, it may not be the optimal choice (in terms of performance in feature extraction) when working with Pandas dataframes. We also offer the possibility to extract a feature table, which requires providing the dataframe and a set of columns to extract as features, and outputs another dataframe with the following columns:

- The case identifier.

- For each string column provided as an attribute, a one-hot encoding (counting the number of occurrences of the given attribute value) for all possible values is performed.

- For every numeric column provided as an attribute, the last value of the attribute in the case is kept.

An example of such feature extraction, keeping `concept:name` (activity) and `amount` (cost) as features in the table, can be calculated as follows:

```python
import pm4py
import pandas as pd
from pm4py.objects.log.util import dataframe_utils

if __name__ == "__main__":
	dataframe = pd.read_csv("tests/input_data/roadtraffic100traces.csv")
	dataframe = pm4py.format_dataframe(dataframe)
	feature_table = dataframe_utils.get_features_df(dataframe, ["concept:name", "amount"])
```

The feature table will contain, in this example, the following columns:
`['case:concept:name', 'concept:name_CreateFine', 'concept:name_SendFine', 'concept:name_InsertFineNotification', 'concept:name_Addpenalty', 'concept:name_SendforCreditCollection', 'concept:name_Payment', 'concept:name_InsertDateAppealtoPrefecture', 'concept:name_SendAppealtoPrefecture', 'concept:name_ReceiveResultAppealfromPrefecture', 'concept:name_NotifyResultAppealtoOffender', 'amount']`

## Discovery of a Data Petri Net

Given a Petri net discovered by a classical process discovery algorithm (e.g., the Alpha Miner or the Inductive Miner), we can transform it into a data Petri net by applying decision mining at every decision point and transforming the resulting decision tree into a guard. An example follows. An event log is loaded, the inductive miner algorithm is applied, and then decision mining is used to discover a data Petri net.

```python
import pm4py
if __name__ == "__main__":
	log = pm4py.read_xes("tests/input_data/roadtraffic100traces.xes")
	net, im, fm = pm4py.discover_petri_net_inductive(log)
	from pm4py.algo.decision_mining import algorithm as decision_mining
	net, im, fm = decision_mining.create_data_petri_nets_with_decisions(log, net, im, fm)
```

The guards discovered for every transition can be printed as follows. They are boolean conditions, which are therefore interpreted by the execution engine.

```python
if __name__ == "__main__":
	for t in net.transitions:
		if "guard" in t.properties:
			print("")
			print(t)
			print(t.properties["guard"])
```

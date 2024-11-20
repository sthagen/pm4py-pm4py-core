

# Conformance Checking


Conformance checking is a techniques to compare a process model with an event log of the
same process. The goal is to check if the event log conforms to the model, and, vice
versa.
In pm4py, two fundamental techniques are implemented: 
token-based replay
 and 
alignments
.



## Token-based replay


Token-based replay matches a trace and a Petri net model, starting from the initial place, in
order to discover which transitions are executed and in which places we have remaining or
missing tokens for the given process instance. Token-based replay is useful for Conformance
Checking: indeed, a trace is fitting according to the model if, during its execution, the
transitions can be fired without the need to insert any missing token. If the reaching of
the final marking is imposed, then a trace is fitting if it reaches the final marking
without any missing or remaining tokens.
See explanation

For each trace, there are four values which have to be determined: 
p
roduced
tokens, 
r
emaining tokens, 
m
issing tokens, and 
c
onsumed tokens.
Based on that, a fomrula can be dervied, whereby a petri net (n) and a trace (t) are
given
as input:
fitness(n,
t)=
1
⁄
2
(1-
r
⁄
p
)+
1
⁄
2
(1-
m
⁄
c
)

To apply the formula on the whole event log, p, r, m, and c are calculated for each
trace, summed up, and finally placed into the formula above at the end.
In pm4py there is an implementation of a token replayer that is able to go across hidden
transitions (calculating shortest paths between places) and can be used with any Petri net
model with unique visible transitions and hidden transitions. When a visible transition
needs to be fired and not all places in the preset are provided with the correct number of
tokens, starting from the current marking it is checked if for some place there is a
sequence of hidden transitions that could be fired in order to enable the visible
transition. The hidden transitions are then fired and a marking that permits to enable the
visible transition is reached.
The example on the right shows how to apply token-based replay
on a log and a Petri net. First, the log is loaded. Then, the Alpha
Miner is applied in order to discover a Petri net.
Eventually, the token-based replay is applied. The output of the token-based replay,
stored in the variable 
replayed_traces
, contains for each trace of the log:
,

- trace_is_fit
: boolean value (True/False) that is true when
the trace is according to the model.
,

- activated_transitions
: list of transitions activated in the model
by the token-based replay.
,

- reached_marking
: marking reached at the end of the replay.
,

- missing_tokens
: number of missing tokens.
,

- consumed_tokens
: number of consumed tokens.
,

- remaining_tokens
: number of remaining tokens.
,

- produced_tokens
: number of produced tokens.



```python
import os
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "running-example.xes"))

	net, initial_marking, final_marking = pm4py.discover_petri_net_alpha(log)

	replayed_traces = pm4py.conformance_diagnostics_token_based_replay(log, net, initial_marking, final_marking)
```




## Diagnostics (TBR)


The execution of token-based replay in pm4py permits to obtain detailed information about
transitions that did not execute correctly, or activities that are in the log and not in the
model. In particular, executions that do not match the model are expected to take longer
throughput time.
The diagnostics that are provided by pm4py are the following:,

- Throughput analysis on the transitions that are executed in an unfit way according to the
process model (the Petri net).,

- Throughput analysis on the activities that are not contained in the model.,

- Root Cause Analysis on the causes that lead to an unfit execution of the transitions.,

- Root Cause Analysis on the causes that lead to executing activities that are not contained
in the process model.
To provide an execution contexts for the examples, a log must be loaded, and a model that
is not perfectly fitting is required. To load the log, the following instructions could
be used:


```python
import os
import pm4py
if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "receipt.xes"))
	log = pm4py.convert_to_event_log(log)
```


To create an unfit model, a filtering operation producing a log where only part of the
behavior is kept can be executed:


```python
import pm4py
if __name__ == "__main__":
	filtered_log = pm4py.filter_variants_top_k(log, 3)
```


Then, applying the Inductive Miner algorithm:


```python
import pm4py
if __name__ == "__main__":
	net, initial_marking, final_marking = pm4py.discover_petri_net_inductive(filtered_log)
```


We then apply the token-based replay with special settings. In particular, with
disable_variants set to True we avoid to replay only a case with variant; with
enable_pltr_fitness set to True we tell the algorithm to return localized Conformance
Checking application.


```python
from pm4py.algo.conformance.tokenreplay import algorithm as token_based_replay
if __name__ == "__main__":
	parameters_tbr = {token_based_replay.Variants.TOKEN_REPLAY.value.Parameters.DISABLE_VARIANTS: True, token_based_replay.Variants.TOKEN_REPLAY.value.Parameters.ENABLE_PLTR_FITNESS: True}
	replayed_traces, place_fitness, trans_fitness, unwanted_activities = token_based_replay.apply(log, net,
																								  initial_marking,
																								  final_marking,
																								  parameters=parameters_tbr)
```


Then, we pass to diagnostics information.
Throughput analysis (unfit execution)
To perform throughput analysis on the transitions that were executed unfit, and then
print on the console the result, the following code could be used:


```python
from pm4py.algo.conformance.tokenreplay.diagnostics import duration_diagnostics
if __name__ == "__main__":
	trans_diagnostics = duration_diagnostics.diagnose_from_trans_fitness(log, trans_fitness)
	for trans in trans_diagnostics:
		print(trans, trans_diagnostics[trans])
```


Obtaining an output where is clear that unfit executions lead to much higher throughput times
(from 126 to 146 times higher throughput time).
Throughput analysis (activities)
To perform throughput analysis on the process executions containing activities that are
not in the model, and then print the result on the screen, the following code could be
used:


```python
from pm4py.algo.conformance.tokenreplay.diagnostics import duration_diagnostics
if __name__ == "__main__":
	act_diagnostics = duration_diagnostics.diagnose_from_notexisting_activities(log, unwanted_activities)
	for act in act_diagnostics:
		print(act, act_diagnostics[act])
```


Root Cause Analysis
The output of root cause analysis in the diagnostics context is a decision tree that permits to
understand the causes of a deviation. In the following examples, for each deviation, a different
decision tree is built and visualized.
In the following examples, that consider the Receipt log, the decision trees will be
built on the following choice of attributes (i.e. only org:group attribute will be
considered).


```python
if __name__ == "__main__":
	# build decision trees
	string_attributes = ["org:group"]
	numeric_attributes = []
	parameters = {"string_attributes": string_attributes, "numeric_attributes": numeric_attributes}
```


Root Cause Analysis (unfit execution)
To perform root cause analysis on the transitions that are executed in an unfit way, the
following code could be used:


```python
from pm4py.algo.conformance.tokenreplay.diagnostics import root_cause_analysis
if __name__ == "__main__":
	trans_root_cause = root_cause_analysis.diagnose_from_trans_fitness(log, trans_fitness, parameters=parameters)
```


To visualize the decision trees obtained by root cause analysis, the following code
could be used:


```python
from pm4py.visualization.decisiontree import visualizer as dt_vis

if __name__ == "__main__":
	for trans in trans_root_cause:
		clf = trans_root_cause[trans]["clf"]
		feature_names = trans_root_cause[trans]["feature_names"]
		classes = trans_root_cause[trans]["classes"]
		# visualization could be called
		gviz = dt_vis.apply(clf, feature_names, classes)
		dt_vis.view(gviz)
```


Root Cause Analysis (activities that are not in the model)
To perform root cause analysis on activities that are executed but are not in the
process model, the following code could be used:


```python
from pm4py.algo.conformance.tokenreplay.diagnostics import root_cause_analysis
if __name__ == "__main__":
	act_root_cause = root_cause_analysis.diagnose_from_notexisting_activities(log, unwanted_activities,
																			  parameters=parameters)
```


To visualize the decision trees obtained by root cause analysis, the following code
could be used:


```python
from pm4py.visualization.decisiontree import visualizer as dt_vis
if __name__ == "__main__":
	for act in act_root_cause:
		clf = act_root_cause[act]["clf"]
		feature_names = act_root_cause[act]["feature_names"]
		classes = act_root_cause[act]["classes"]
		# visualization could be called
		gviz = dt_vis.apply(clf, feature_names, classes)
		dt_vis.view(gviz)
```




## Alignments


pm4py comes with the following set of linear solvers: Scipy (available for any platform),
CVXOPT (available for the most widely used platforms including Windows/Linux).
Alternatively, ORTools can also be used and installed from PIP.
Alignment-based replay aims to find one of the best alignment between the trace and the
model. For each trace, the output of an alignment is a list of couples where the first
element is an event (of the trace) or » and the second element is a transition (of the
model) or ». For each couple, the following classification could be provided:,

- Sync move: the classification of the event corresponds to the transition label; in this
case, both the trace and the model advance in the same way during the replay.,

- Move on log: for couples where the second element is », it corresponds to a replay move
in the trace that is not mimicked in the model. This kind of move is unfit and signal a
deviation between the trace and the model.,

- Move on model: for couples where the first element is », it corresponds to a replay move
in the model that is not mimicked in the trace. For moves on model, we can have the
following distinction:
,

- - Moves on model involving hidden transitions: in this case, even if it is not a
sync move, the move is fit.,

- - Moves on model not involving hidden transitions: in this case, the move is unfit
and signals a deviation between the trace and the model.
First, we have to import the log. Subsequently, we apply the Inductive Miner on the
imported log. In addition, we compute the alignments.


```python
import os
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "running-example.xes"))
	log = pm4py.convert_to_event_log(log)

	net, initial_marking, final_marking = pm4py.discover_petri_net_inductive(log)

	import pm4py
	aligned_traces = pm4py.conformance_diagnostics_alignments(log, net, initial_marking, final_marking)
```


To inspect the alignments, a code snippet is provided. However, the output (a list)
reports for each trace the corresponding alignment along with its statistics. With
each trace, a dictionary containing among the others the following information is
associated:,

- alignment
: contains the alignment (sync moves, moves on log, moves on model)
,

- cost
: contains the cost of the alignment according to the provided cost
function
,

- fitness
: is equal to 1 if the trace is perfectly fitting


```python
print(alignments)
```


To use a different classifier, we refer to the 
Classifier
section (#item-3-7)
. However, the following code defines a
custom classifier for each
event of each trace in the log.


```python
if __name__ == "__main__":
	for trace in log:
	 for event in trace:
	  event["customClassifier"] = event["concept:name"] + event["concept:name"]
```


A parameters dictionary containing the activity key can be formed.


```python
# define the activity key in the parameters
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.algo.conformance.alignments.petri_net import algorithm as alignments
from pm4py.objects.conversion.process_tree import converter as process_tree_converter
parameters = {"pm4py:param:activity_key": "customClassifier"}
```


Then, a process model is computed, and alignments are also calculated. Besides, the
fitness value is calculated and the resulting values are printed.


```python
# calculate process model using the given classifier
if __name__ == "__main__":
	process_tree = inductive_miner.apply(log, parameters=parameters)
	net, initial_marking, final_marking = process_tree_converter.apply(process_tree)
	aligned_traces = alignments.apply_log(log, net, initial_marking, final_marking, parameters=parameters)

	from pm4py.algo.evaluation.replay_fitness import algorithm as replay_fitness
	log_fitness = replay_fitness.evaluate(aligned_traces, variant=replay_fitness.Variants.ALIGNMENT_BASED)

	print(log_fitness)
```


It is also possible to select other parameters for the alignments.,

- Model cost function: associating to each transition in the Petri net the corresponding
cost of a move-on-model.,

- Sync cost function: associating to each visible transition in the Petri net the cost of
a sync move.
On the right-hand side, an implementation of a custom model cost function, and sync
cost function can be noted. Also, the model cost funtions and sync cost function has
to be inserted later in the parameters. Subsequently, the replay is done.


```python
if __name__ == "__main__":
	model_cost_function = dict()
	sync_cost_function = dict()
	for t in net.transitions:
	 # if the label is not None, we have a visible transition
	 if t.label is not None:
	  # associate cost 1000 to each move-on-model associated to visible transitions
	  model_cost_function[t] = 1000
	  # associate cost 0 to each move-on-log
	  sync_cost_function[t] = 0
	 else:
	  # associate cost 1 to each move-on-model associated to hidden transitions
	  model_cost_function[t] = 1

	parameters = {}
	parameters[alignments.Variants.VERSION_STATE_EQUATION_A_STAR.value.Parameters.PARAM_MODEL_COST_FUNCTION] = model_cost_function
	parameters[alignments.Variants.VERSION_STATE_EQUATION_A_STAR.value.Parameters.PARAM_SYNC_COST_FUNCTION] = sync_cost_function

	aligned_traces = alignments.apply_log(log, net, initial_marking, final_marking, parameters=parameters)
```




## Decomposition of Alignments


Alignments represent a computationally expensive problem on models that contain a lot of
concurrency. Yet, they are the conformance checking technique that provides the best results in
term of finding a match between the process execution(s) and the model. To overcome the
difficulties related to the size of the state space, various attempts to decompose the model
into “smaller” pieces, into which the alignment is easier and still permit to diagnose problems,
have been done.
We have seen how to obtain a maximal decomposition of the Petri net model. Now we can see
how to perform the decomposition of alignments (that is based on a maximal decomposition
of the Petri net model). The approach described here has been published in:
Lee, Wai Lam Jonathan, et al. “Recomposing conformance: Closing the circle on decomposed
alignment-based conformance checking in process mining.” Information Sciences 466 (2018):
55-91.

The recomposition permits to understand whether each step of the process has been executed in a
sync way or some deviations happened. First, an alignment is performed on top of the decomposed
Petri nets.
Then, the agreement between the activities at the border is checked. If a disagreement is found,
the two components that are disagreeing are merged and the alignment is repeated on them.
When the steps are agreeing between the different alignments of the components, these can be
merged in a single alignment. The order of recomposition is based on the Petri net graph.
Despite that, in the case of concurrency, the “recomposed” alignment contains a valid list of
moves that may not be in the correct order.
To perform alignments through decomposition/recomposition, the following code can be
used. A maximum number of border disagreements can be provided to the algorithm. If the
number of border disagreements is reached, then the alignment is interrupted a None as
alignment of the specific trace is returned.


```python
from pm4py.algo.conformance.alignments.decomposed import algorithm as decomp_alignments

if __name__ == "__main__":
	conf = decomp_alignments.apply(log, net, initial_marking, final_marking, parameters={decomp_alignments.Variants.RECOMPOS_MAXIMAL.value.Parameters.PARAM_THRESHOLD_BORDER_AGREEMENT: 2})
```


Since decomposed models are expected to have less concurrency, the components are aligned using
a Dijkstra approach. In the case of border disagreements, this can degrade the performance of
the algorithm.
It should be noted that this is not an approximation technique;
according to the authors, it should provide the same fitness
as the original alignments.
Since the alignment is recomposed, we can use the fitness evaluator to evaluate
the fitness (that is not related to the computation of fitness described in the paper).



```python
from pm4py.algo.evaluation.replay_fitness import algorithm as rp_fitness_evaluator

if __name__ == "__main__":
	fitness = rp_fitness_evaluator.evaluate(conf, variant=rp_fitness_evaluator.Variants.ALIGNMENT_BASED)
```




## Footprints


Footprints are a very basic (but scalable) conformance checking technique to compare entities
(such that event logs, DFGs, Petri nets, process trees, any other kind of model).
Essentially, a relationship between any couple of activities of the log/model is inferred. This
can include:,

- Directly-Follows Relationships: in the log/model, it is possible that the activity A is
directly followed by B.,

- Directly-Before Relationships: in the log/model, it is possible that the activity B is
directly preceded by A.,

- Parallel behavior: it is possible that A is followed by B and B is followed by A
A footprints matrix can be calculated, that describes for each couple of activities the
footprint relationship.
It is possible to calculate that for different types of models and for the entire event log,
but also trace-by-trace (if the local behavior is important).
Let’s assume that the running-example.xes event log is loaded:



```python
import pm4py
import os
if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "running-example.xes"))
```


And the inductive miner is applied on such log:



```python
if __name__ == "__main__":
	net, im, fm = pm4py.discover_petri_net_inductive(log)
```


To calculate the footprints for the entire log, the following code can be used:



```python
from pm4py.algo.discovery.footprints import algorithm as footprints_discovery

if __name__ == "__main__":
	fp_log = footprints_discovery.apply(log, variant=footprints_discovery.Variants.ENTIRE_EVENT_LOG)
```


The footprints of the entire log are:
{‘sequence’: {(‘examine casually’, ‘decide’), (‘decide’, ‘pay compensation’), (‘register
request’, ‘examine thoroughly’), (‘reinitiate request’, ‘examine casually’), (‘check
ticket’, ‘decide’), (‘register request’, ‘examine casually’), (‘reinitiate request’,
‘examine thoroughly’), (‘decide’, ‘reject request’), (‘examine thoroughly’, ‘decide’),
(‘reinitiate request’, ‘check ticket’), (‘register request’, ‘check ticket’), (‘decide’,
‘reinitiate request’)}, ‘parallel’: {(‘examine casually’, ‘check ticket’), (‘check ticket’,
‘examine casually’), (‘check ticket’, ‘examine thoroughly’), (‘examine thoroughly’, ‘check
ticket’)}, ‘start_activities’: {‘register request’}, ‘end_activities’: {‘pay compensation’,
‘reject request’}, ‘activities’: {‘reject request’, ‘register request’, ‘check ticket’,
‘decide’, ‘pay compensation’, ‘examine thoroughly’, ‘examine casually’, ‘reinitiate
request’}}

The data structure is a dictionary with, as keys, sequence (expressing directly-follows
relationships) and parallel (expressing the parallel behavior that can happen in either way).
The footprints of the log, trace-by-trace, can be calculated as follows, and are a list of
footprints for each trace:



```python
from pm4py.algo.discovery.footprints import algorithm as footprints_discovery

if __name__ == "__main__":
	fp_trace_by_trace = footprints_discovery.apply(log, variant=footprints_discovery.Variants.TRACE_BY_TRACE)
```


The footprints of the Petri net model can be calculated as follows:



```python
if __name__ == "__main__":
	fp_net = footprints_discovery.apply(net, im, fm)
```


And are the following:
{‘sequence’: {(‘check ticket’, ‘decide’), (‘reinitiate request’, ‘examine casually’),
(‘register request’, ‘examine thoroughly’), (‘decide’, ‘reject request’), (‘register
request’, ‘check ticket’), (‘register request’, ‘examine casually’), (‘decide’, ‘reinitiate
request’), (‘reinitiate request’, ‘examine thoroughly’), (‘decide’, ‘pay compensation’),
(‘reinitiate request’, ‘check ticket’), (‘examine casually’, ‘decide’), (‘examine
thoroughly’, ‘decide’)}, ‘parallel’: {(‘check ticket’, ‘examine thoroughly’), (‘examine
thoroughly’, ‘check ticket’), (‘check ticket’, ‘examine casually’), (‘examine casually’,
‘check ticket’)}, ‘activities’: {‘decide’, ‘examine casually’, ‘reinitiate request’, ‘check
ticket’, ‘examine thoroughly’, ‘register request’, ‘reject request’, ‘pay compensation’},
‘start_activities’: {‘register request’}}

The data structure is a dictionary with, as keys, sequence (expressing directly-follows
relationships) and parallel (expressing the parallel behavior that can happen in either way).
It is possible to visualize a comparison between the footprints of the (entire) log and the
footprints of the (entire) model.
First of all, let’s see how to visualize a single footprints table, for example the one of
the model. The following code can be used:



```python
from pm4py.visualization.footprints import visualizer as fp_visualizer

if __name__ == "__main__":
	gviz = fp_visualizer.apply(fp_net, parameters={fp_visualizer.Variants.SINGLE.value.Parameters.FORMAT: "svg"})
	fp_visualizer.view(gviz)
```


To compare the two footprints tables, the following code can be used. Please note that the
visualization will look the same, if no deviations are discovered. If deviations are found
they are colored by red.



```python
from pm4py.visualization.footprints import visualizer as fp_visualizer

if __name__ == "__main__":
	gviz = fp_visualizer.apply(fp_log, fp_net, parameters={fp_visualizer.Variants.COMPARISON.value.Parameters.FORMAT: "svg"})
	fp_visualizer.view(gviz)
```


To actually find some deviations, let’s repeat the procedure on the receipt.xes log,
applying a heavy filter on the log to discover a simpler model:



```python
import pm4py
import os
from copy import deepcopy

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "receipt.xes"))
	filtered_log = pm4py.filter_variants_top_k(log, 3)

	net, im, fm = pm4py.discover_petri_net_inductive(filtered_log)
```


With a conformance checking operation, we want instead to compare the behavior of the traces
of the log against the footprints of the model.
This can be done using the following code:



```python
if __name__ == "__main__":
	conf_fp = pm4py.conformance_diagnostics_footprints(fp_trace_by_trace, fp_net)
```


And will contain, for each trace of the log, a set with the deviations. Extract of the list for
some traces:
{(‘T06 Determine necessity of stop advice’, ‘T04 Determine confirmation of receipt’), (‘T02
Check confirmation of receipt’, ‘T06 Determine necessity of stop advice’)}
set()
{(‘T19 Determine report Y to stop indication’, ‘T20 Print report Y to stop indication’),
(‘T10 Determine necessity to stop indication’, ‘T16 Report reasons to hold request’), (‘T16
Report reasons to hold request’, ‘T17 Check report Y to stop indication’), (‘T17 Check
report Y to stop indication’, ‘T19 Determine report Y to stop indication’)}
set()
set()
{(‘T02 Check confirmation of receipt’, ‘T06 Determine necessity of stop advice’), (‘T10
Determine necessity to stop indication’, ‘T04 Determine confirmation of receipt’), (‘T04
Determine confirmation of receipt’, ‘T03 Adjust confirmation of receipt’), (‘T03 Adjust
confirmation of receipt’, ‘T02 Check confirmation of receipt’)}
set()
We can see that for the first trace that contains deviations, there are two deviations, the
first related to T06 Determine necessity of stop advice being executed before T04 Determine
confirmation of receipt; the second related to T02 Check confirmation of receipt being followed
by T06 Determine necessity of stop advice.
The traces for which the conformance returns nothing are fit (at least according to the
footprints).
Footprints conformance checking is a way to identify obvious deviations, behavior of the log
that is not allowed by the model.
On the log side, their scalability is wonderful! The calculation of footprints for a Petri net
model may be instead more expensive.
If we change the underlying model, from Petri nets to process tree, it is possible to exploit
its bottomup structure in order to calculate the footprints almost instantaneously.
Let’s open a log, calculate a process tree and then apply the discovery of the footprints.
We open the running-example log:



```python
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes("tests/input_data/running-example.xes")
```


And apply the inductive miner to discover a process tree:



```python
if __name__ == "__main__":
	tree = pm4py.discover_process_tree_inductive(log)
```


Then, the footprints can be discovered. We discover the footprints on the entire log, we
discover the footprints trace-by-trace in the log, and then we discover the footprints on
the process tree:



```python
from pm4py.algo.discovery.footprints import algorithm as fp_discovery

if __name__ == "__main__":
	fp_log = fp_discovery.apply(log, variant=fp_discovery.Variants.ENTIRE_EVENT_LOG)
	fp_trace_trace = fp_discovery.apply(log, variant=fp_discovery.Variants.TRACE_BY_TRACE)
	fp_tree = fp_discovery.apply(tree, variant=fp_discovery.Variants.PROCESS_TREE)
```


Each one of these contains:,

- A list of sequential footprints contained in the log/allowed by the model,

- A list of parallel footprints contained in the log/allowed by the model,

- A list of activities contained in the log/allowed by the model,

- A list of start activities contained in the log/allowed by the model,

- A list of end activities contained in the log/allowed by the model
It is possible to execute an enhanced conformance checking between the footprints of the
(entire) log, and the footprints of the model, by doing:



```python
from pm4py.algo.conformance.footprints import algorithm as fp_conformance

if __name__ == "__main__":
	conf_result = fp_conformance.apply(fp_log, fp_tree, variant=fp_conformance.Variants.LOG_EXTENSIVE)
```


The result contains, for each item of the previous list, the violations.
Given the result of conformance checking, it is possible to calculate the footprints-based
fitness and precision of the process model, by doing:



```python
from pm4py.algo.conformance.footprints.util import evaluation

if __name__ == "__main__":
	fitness = evaluation.fp_fitness(fp_log, fp_tree, conf_result)
	precision = evaluation.fp_precision(fp_log, fp_tree)
```


These values are both included in the interval [0,1]


## Log Skeleton


The concept of log skeleton has been described in the contribution
Verbeek, H. M. W., and R. Medeiros de Carvalho. “Log skeletons: A classification approach to
process discovery.” arXiv preprint arXiv:1806.08247 (2018).

And is claimingly the most accurate classification approach to decide whether a trace belongs to
(the language) of a log or not.
For a log, an object containing a list of relations is calculated.

Inspect relations
,

- Equivalence:
 contains the couples of activities that happen ALWAYS with the same
frequency inside a trace.
,

- Always-after
: contains the couples of activities (A,B) such that an occurrence of
A is ALWAYS followed, somewhen in the future of the trace, by an occurrence of B.
,

- Always-before
: contains the couples of activities (B,A) such that an occurrence
of B is ALWAYS preceded, somewhen in the past of the trace, by an occurrence of A.
,

- Never-together
: contains the couples of activities (A,B) that NEVER happens
together in the history of the trace.
,

- Directly-follows
: contains the list of directly-follows relations of the log.
,

- For each activity, the 
number of possible occurrences
 per trace.

It is also possible to provide a noise threshold. In that case, more relations are found since
the conditions are relaxed.
Let’s suppose to take the running-example.xes log:



```python
import pm4py
import os
if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "running-example.xes"))
```


Then, we can calculate the log skeleton:



```python
from pm4py.algo.discovery.log_skeleton import algorithm as lsk_discovery
if __name__ == "__main__":
	skeleton = lsk_discovery.apply(log, parameters={lsk_discovery.Variants.CLASSIC.value.Parameters.NOISE_THRESHOLD: 0.0})
```


We can also print that:
{‘equivalence’: {(‘pay compensation’, ‘register request’), (‘examine thoroughly’, ‘register
request’), (‘reject request’, ‘register request’), (‘pay compensation’, ‘examine
casually’)}, ‘always_after’: {(‘register request’, ‘check ticket’), (‘examine thoroughly’,
‘decide’), (‘register request’, ‘decide’)}, ‘always_before’: {(‘pay compensation’, ‘register
request’), (‘pay compensation’, ‘decide’), (‘pay compensation’, ‘check ticket’), (‘reject
request’, ‘decide’), (‘pay compensation’, ‘examine casually’), (‘reject request’, ‘check
ticket’), (‘examine thoroughly’, ‘register request’), (‘reject request’, ‘register
request’)}, ‘never_together’: {(‘pay compensation’, ‘reject request’), (‘reject request’,
‘pay compensation’)}, ‘directly_follows’: set(), ‘activ_freq’: {‘register request’: {1},
‘examine casually’: {0, 1, 3}, ‘check ticket’: {1, 2, 3}, ‘decide’: {1, 2, 3}, ‘reinitiate
request’: {0, 1, 2}, ‘examine thoroughly’: {0, 1}, ‘pay compensation’: {0, 1}, ‘reject
request’: {0, 1}}}

We can see the relations (equivalence, always_after, always_before, never_together,
directly_follows, activ_freq) as key of the object, and the values are the activities/couples of
activities that follow such pattern.
To see how the log skeleton really works, for classification/conformance purposes, let’s
change to another log (the receipt.xes log), and calculate an heavily filtered version of
that (to have less behavior)



```python
import pm4py
import os
if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "receipt.xes"))
	from copy import deepcopy
	filtered_log = pm4py.filter_variants_top_k(log, 3)
```


Calculate the log skeleton on top of the filtered log, and then apply the classification as
follows:



```python
from pm4py.algo.conformance.log_skeleton import algorithm as lsk_conformance
if __name__ == "__main__":
	conf_result = lsk_conformance.apply(log, skeleton)
```


In such way, we can get for each trace whether it has been classified as belonging to the
filtered log, or not. When deviations are found, the trace does not belong to the language of
the original log.
We can also calculate a log skeleton on the original log, for example providing 0.03 as
noise threshold, and see which are the effects on the classification:



```python
from pm4py.algo.discovery.log_skeleton import algorithm as lsk_discovery
from pm4py.algo.conformance.log_skeleton import algorithm as lsk_conformance

if __name__ == "__main__":
	skeleton = lsk_discovery.apply(log, parameters={lsk_discovery.Variants.CLASSIC.value.Parameters.NOISE_THRESHOLD: 0.03})

	conf_result = lsk_conformance.apply(log, skeleton)
```


We can see that some traces are classified as uncorrect also calculating the log skeleton on the
original log, if a noise threshold is provided.


## Alignments between Logs


In some situations, performing an optimal alignment between an event log and a process model might
be unfeasible. Hence, getting an approximated alignment that highlights the main points of deviation
is an option. In pm4py, we offer support for alignments between two event logs. Such alignment
operation is based on the edit distance, i.e., for a trace of the first log, the trace of the second log
which has the least edit distance is found. In the following example, we see how to perform
alignments between an event log and the simulated log obtained by performing a playout operation
on the process model.
We can load an example log and discover a process model using the inductive miner:



```python
import pm4py
if __name__ == "__main__":
	log = pm4py.read_xes("tests/input_data/running-example.xes")
	net, im, fm = pm4py.discover_petri_net_inductive(log)
```


Then, perform a playout operation on the process model:



```python
if __name__ == "__main__":
	simulated_log = pm4py.play_out(net, im, fm)
```


Then, the alignments between the two logs are performed:



```python
from pm4py.algo.conformance.alignments.edit_distance import algorithm as logs_alignments
if __name__ == "__main__":
	alignments = logs_alignments.apply(log, simulated_log)
```


The result is a list of alignments, each one contains a list of moves (sync move, move on log n.1, move on log n.2).
With this utility, it's also possible to perform anti-alignments. In this case, an anti-alignment is corresponding to
a trace of the second log that has the biggest edit distance against the given trace of the first log.
To perform anti-alignments, the following code can be used:



```python
from pm4py.algo.conformance.alignments.edit_distance import algorithm as logs_alignments
if __name__ == "__main__":
	parameters = {logs_alignments.Variants.EDIT_DISTANCE.value.Parameters.PERFORM_ANTI_ALIGNMENT: True}
	alignments = logs_alignments.apply(log, simulated_log, parameters=parameters)
```




## Temporal Profile


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
The output of conformance checking based on a temporal profile is a list containing the deviations for each case in the log.
Each deviation is expressed as a couple of activities, along with the calculated value and the distance (based on number of standard deviations)
from the average.
We provide an example of conformance checking based on a temporal profile.
First, we can load an event log, and apply the discovery algorithm.



```python
import pm4py
from pm4py.algo.discovery.temporal_profile import algorithm as temporal_profile_discovery

if __name__ == "__main__":
	log = pm4py.read_xes("tests/input_data/receipt.xes")
	temporal_profile = temporal_profile_discovery.apply(log)
```


Then, we can apply conformance checking based on the temporal profile.



```python
from pm4py.algo.conformance.temporal_profile import algorithm as temporal_profile_conformance
if __name__ == "__main__":
	results = temporal_profile_conformance.apply(log, temporal_profile)
```


Some parameters can be used in order to customize the conformance checking of the temporal profile:
See Parameters



|Parameter Key|Type|Default|Description|
|---|---|---|---|
|Parameters.ACTIVITY_KEY|string|concept:name|The attribute to use as activity.|
|Parameters.START_TIMESTAMP_KEY|string|start_timestamp|The attribute to use as start timestamp.|
|Parameters.TIMESTAMP_KEY|string|time:timestamp|The attribute to use as timestamp.|
|Parameters.ZETA|int|6|Multiplier for the standard deviation. Couples of events that are more distant than this are signaled by the temporal profile.|





## LTL Checking


LTL Checking is a form of filtering/conformance checking in which some rules are
verified against the process executions contained in the log.
This permits to check more complex patterns such as:,

- Four eyes principle
: two given activities should be executed by two
different people. For example, the approval of an expense refund should be generally
done by a different person rather than the insertion of the expense refund.,

- Activity repeated by different people
: the same activity in a process
execution is repeated (that means rework) from different people.
The verification of LTL rules requires the insertion of the required parameters
(of the specific rule). Hence, this form of conformance checking is not automatic.
The LTL rules that are implemented in pm4py are found in the following table:


|LTL rule|Description|
|---|---|
|ltl.ltl_checker.four_eyes_principle(log, A, B)|Applies the four eyes principle on the activities A and B. Parameters: log: event log A: the activity A of the rule (an activity of the log) B: the activity B of the rule (an activity of the log) Returns: Filtered log object (containing the cases which have A and B done by the same person)|
|ltl.ltl_checker.attr_value_different_persons(log, A)|Finds the process executions in which the activity A is repeated by different people. Parameters: log: event log A: the activity A of the rule (an activity of the log) Returns: Filtered log object (containing the cases which have A repeated by different people)|



The rules can be applied on both traditional event logs (XES) and Pandas dataframes,
by looking at the packages 
pm4py.algo.filtering.log.ltl
and 
pm4py.algo.filtering.pandas.ltl
 respectively.
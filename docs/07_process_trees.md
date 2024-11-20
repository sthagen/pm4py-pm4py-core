

# Process Trees


In pm4py we offer support for process trees (visualization, conversion to Petri net and
generation of a log), for importing/exporting, and a functionality to generate them. In this
section, the
functionalities are examined.


## Importing/Exporting Process Trees


In pm4py, we offer support for importing/exporting process trees in the PTML format.
The following code can be used to import a process tree from a PTML file.


```python
import pm4py

if __name__ == "__main__":
	tree = pm4py.read_ptml("tests/input_data/running-example.ptml")
```


The following code can be used to export a process tree into a PTML file.


```python
import pm4py

if __name__ == "__main__":
	pm4py.write_ptml(tree, "running-example.ptml")
```




## Generation of process trees


The approach 'PTAndLogGenerator', described by the scientific paper 'PTandLogGenerator: A
Generator for Artificial Event Data', has been implemented in the pm4py library.
The code snippet can be used to generate a process tree.
Inspect parameters



```python
import pm4py
if __name__ == "__main__":
	tree = pm4py.generate_process_tree()
```


Suppose the following start activity and their respective occurrences.



|Parameter|Meaning|
|---|---|
|MODE|most frequent number of visible activities (default 20)|
|MIN|minimum number of visible activities (default 10)|
|MAX|maximum number of visible activities (default 30)|
|SEQUENCE|probability to add a sequence operator to tree (default 0.25)|
|CHOICE|probability to add a choice operator to tree (default 0.25)|
|PARALLEL|probability to add a parallel operator to tree (default 0.25)|
|LOOP|probability to add a loop operator to tree (default 0.25)|
|OR|probability to add an or operator to tree (default 0)|
|SILENT|probability to add silent activity to a choice or loop operator (default 0.25)|
|DUPLICATE|probability to duplicate an activity label (default 0)|
|LT_DEPENDENCY|probability to add a random dependency to the tree (default 0)|
|INFREQUENT|probability to make a choice have infrequent paths (default 0.25)|
|NO_MODELS|number of trees to generate from model population (default 10)|
|UNFOLD|whether or not to unfold loops in order to include choices underneath in dependencies: 0=False, 1=True if lt_dependency <= 0: this should always be 0 (False) if lt_dependency > 0: this can be 1 or 0 (True or False) (default 10)|
|MAX_REPEAT|maximum number of repetitions of a loop (only used when unfolding is True) (default 10)|





## Generation of a log out of a process tree


The code snippet can be used to generate a log, with 100 cases, out of the process tree.



```python
import pm4py
if __name__ == "__main__":
	log = pm4py.play_out(tree)
	print(len(log))
```




## Conversion into Petri net


The code snippet can be used to convert the process tree into a Petri net.



```python
import pm4py
if __name__ == "__main__":
	net, im, fm = pm4py.convert_to_petri_net(tree)
```




## Visualize a Process Tree


A process tree can be printed, as revealed on the right side.



```python
if __name__ == "__main__":
	print(tree)
```


A process tree can also be visualized, as revealed on the right side.



```python
import pm4py
if __name__ == "__main__":
	pm4py.view_process_tree(tree, format='png')
```




## Converting a Petri net to a Process Tree


We propose an approach to convert a block-structured accepting Petri net to a process
tree. The implement approach is:
van Zelst, Sebastiaan J. "Translating Workflow Nets to Process Trees: An Algorithmic
Approach." arXiv preprint arXiv:2004.08213 (2020).
The approach, given an accepting Petri net, returns a process tree if the Petri net
is block-structured, while it raises an exception if the Petri net is not block-structured.
We propose an example of application. First, we load a XES log and we discover an accepting
Petri net
using the Alpha Miner algorithm.



```python
import pm4py
import os

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "running-example.xes"))
	net, im, fm = pm4py.discover_petri_net_alpha(log)
```


Then, we convert that to a process tree.



```python
import pm4py

if __name__ == "__main__":
	tree = pm4py.convert_to_process_tree(net, im, fm)
	print(tree)
```


The method succeeds, since the accepting Petri net is block-structured, and discovers a process
tree
(incidentally, the same process tree as if the inductive miner was applied).


## Frequency Annotation of a Process Tree


A process tree does not include
any frequency/performance annotation by default.
A log can be matched against a process tree in an optimal way using the alignments
algorithm. The results of the alignments algorithm contains the list of leaves/operators
visited during the replay. This can be used to infer the frequency at the case/event level
of every node of the process tree.
The following code can be used to decorate the frequency of the nodes of a process tree:



```python
import pm4py
from pm4py.algo.conformance.alignments.process_tree.util import search_graph_pt_frequency_annotation
if __name__ == "__main__":
	aligned_traces = pm4py.conformance_diagnostics_alignments(log, tree)
	tree = search_graph_pt_frequency_annotation.apply(tree, aligned_traces)
```


A frequency-based visualization of the process tree is also available:



```python
from pm4py.visualization.process_tree import visualizer as pt_visualizer
if __name__ == "__main__":
	gviz = pt_visualizer.apply(tree, parameters={"format": "svg"}, variant=pt_visualizer.Variants.FREQUENCY_ANNOTATION)
	pt_visualizer.view(gviz)
```


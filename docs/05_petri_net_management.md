

# Petri Net management


Petri nets are one of the most common formalism to express a process model. A Petri net
is a directed bipartite graph, in which the nodes represent transitions and places. Arcs
are connecting places to transitions and transitions to places, and have an associated
weight. A transition can fire if each of its input places contains a number of tokens
that is at least equal to the weight of the arc connecting the place to the transition.
When a transition is fired, then tokens are removed from the input places according to
the weight of the input arc, and are added to the output places according to the weight
of the output arc.
A marking is a state in the Petri net that associates each place to a number of tokens
and is uniquely associated to a set of enabled transitions that could be fired according
to the marking.
Process Discovery algorithms implemented in pm4py returns a Petri net along with an
initial marking and a final marking. An initial marking is the initial state of
execution of a process, a final marking is a state that should be reached at the end of
the execution of the process.


## Importing and exporting


Petri nets, along with their initial and final marking, can be imported/exported from the
PNML file format. The code on the right-hand side can be used to import a Petri net along
with the
initial and final marking.
First, we have to import the log. Subsequently, the Petri net is visualized by using
the Petri Net visualizer. In addition, the Petri net is exported with its initial
marking or initial marking and final marking.


```python
import os
import pm4py

if __name__ == "__main__":
	net, initial_marking, final_marking = pm4py.read_pnml(os.path.join("tests","input_data","running-example.pnml"))
	pm4py.view_petri_net(net, initial_marking, final_marking)

	pm4py.write_pnml(net, initial_marking, final_marking, "petri.pnml")
```




## Petri Net properties


This section is about how to get the properties of a Petri Net. A property of the pet is, for
example, a the enabled transition in a particular marking. However, also a list of places,
transitions or arcs can be inspected.
The list of transitions enabled in a particular marking can be obtained using the
right-hand code.


```python
from pm4py.objects.petri_net import semantics

if __name__ == "__main__":
	transitions = semantics.enabled_transitions(net, initial_marking)
```


The function 
`print(transitions)`
 reports that only the transition
register request is
enabled in the initial marking in the given Petri net. To obtain all places,
transitions, and arcs of the Petri net, the code which can be obtained on the
right-hand side can be used.


```python
if __name__ == "__main__":
	places = net.places
	transitions = net.transitions
	arcs = net.arcs
```


Each place has a name and a set of input/output arcs (connected at source/target to a
transition). Each transition has a name and a label and a set of input/output arcs
(connected at source/target to a place). The code on the right-hand side prints for
each place the name, and for each input arc of the place the name and the label of
the corresponding transition. However, there also exsits 
`trans.name`
,
`trans.label`
, 
`arc.target.name`
.


```python
if __name__ == "__main__":
	for place in places:
	 print("\nPLACE: "+place.name)
	 for arc in place.in_arcs:
	  print(arc.source.name, arc.source.label)
```




## Creating a new Petri Net


In this section, an overview of the code necessary to create a new Petri net with places,
transitions, and arcs is provided. A Petri net object in pm4py should be created with a
name.
The code on the right-hand side creates a Petri Net with the name

`new_petri_net`
.


```python
# creating an empty Petri net
from pm4py.objects.petri_net.obj import PetriNet, Marking

if __name__ == "__main__":
	net = PetriNet("new_petri_net")
```


In addition, three places are created, namely 
`source`
,
`sink`
, and 
`p_1`
. These places are added to the previously
created Petri Net.


```python
if __name__ == "__main__":
	# creating source, p_1 and sink place
	source = PetriNet.Place("source")
	sink = PetriNet.Place("sink")
	p_1 = PetriNet.Place("p_1")
	# add the places to the Petri Net
	net.places.add(source)
	net.places.add(sink)
	net.places.add(p_1)
```


Similar to the places, transitions can be created. However, they need to be assigned
a name and a label.


```python
if __name__ == "__main__":
	# Create transitions
	t_1 = PetriNet.Transition("name_1", "label_1")
	t_2 = PetriNet.Transition("name_2", "label_2")
	# Add the transitions to the Petri Net
	net.transitions.add(t_1)
	net.transitions.add(t_2)
```


Arcs that connect places with transitions or transitions with places might
be necessary. To add arcs, code is provided. The first parameter specifies the
starting point of the arc, the second parameter its target and the last parameter
states the Petri net it belongs to.


```python
# Add arcs
if __name__ == "__main__":
	from pm4py.objects.petri_net.utils import petri_utils
	petri_utils.add_arc_from_to(source, t_1, net)
	petri_utils.add_arc_from_to(t_1, p_1, net)
	petri_utils.add_arc_from_to(p_1, t_2, net)
	petri_utils.add_arc_from_to(t_2, sink, net)
```


To complete the Petri net, an initial and possibly a final marking need to be
defined.
To accomplish this, we define the initial marking to contain 1 token in the source
place and the final marking to contain 1 token in the sink place.


```python
# Adding tokens
if __name__ == "__main__":
	initial_marking = Marking()
	initial_marking[source] = 1
	final_marking = Marking()
	final_marking[sink] = 1
```


The resulting Petri net along with the initial and final marking can be exported, or
visualized.


```python
import pm4py
if __name__ == "__main__":
	pm4py.write_pnml(net, initial_marking, final_marking, "createdPetriNet1.pnml")

	pm4py.view_petri_net(net, initial_marking, final_marking)
```


To obtain a specific output format (e.g. svg or png) a format parameter should be
provided to the algorithm. The code snippet explains how to obtain an SVG
representation of the Petri net. The last lines provide an option to save the
visualization of the model.


```python
import pm4py
if __name__ == "__main__":
	pm4py.view_petri_net(net, initial_marking, final_marking, format="svg")
	pm4py.save_vis_petri_net(net, initial_marking, final_marking, "net.svg")
```




## Maximal Decomposition


The decomposition technique proposed in this section
is useful for conformance checking purpose. Indeed, splitting
the overall model in smaller models can reduce the size of the
state space, hence increasing the performance of the conformance checking operation.
We propose to use the decomposition technique (maximal decomposition of a Petri net) described
in:
Van der Aalst, Wil MP. “Decomposing Petri nets for process mining: A generic approach.”
Distributed and Parallel Databases 31.4 (2013): 471-507.

We can see an example of maximal decomposition on top of the Petri net extracted by
the Alpha Miner on top of the Running Example log.
Let’s first load the running example log and apply the Alpha Miner.


```python
import os
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "running-example.xes"))
	net, im, fm = pm4py.discover_petri_net_alpha(log)
```


Then, the decomposition can be found using:


```python
from pm4py.objects.petri_net.utils.decomposition import decompose

if __name__ == "__main__":
	list_nets = decompose(net, im, fm)
```


If we want to represent each one of the Petri nets, we can use a FOR loop:


```python
import pm4py

if __name__ == "__main__":
	for index, model in enumerate(list_nets):
		subnet, s_im, s_fm = model

		pm4py.save_vis_petri_net(subnet, s_im, s_fm, str(index)+".png")
```


A log that is fit according to the original model is also fit (projecting on the activities of
the net) for these nets. Conversely, any deviation on top of these models represent a deviation
also on the original model.


## Reachability Graph


A reachability graph is a transition system that can constructed on any
Petri net along with an initial marking, and is the graph of all the
markings of the Petri net. These markings are connected by as many edges
as many transitions connect the two different markings.
The main goal of the reachability graph is to provide an understanding of the state space
of the Petri net. Usually, Petri nets containing a lot of concurrency have
an incredibly big reachability graph. The same computation of the reachability
graph may be unfeasible for such models.
The calculation of the reachability graph, having the Petri net
and the initial marking, can be done with the
following code:



```python
from pm4py.objects.petri_net.utils import reachability_graph

if __name__ == "__main__":
	ts = reachability_graph.construct_reachability_graph(net, im)
```


The visualization of the reachability graph is then possible
through the code snippet:



```python
from pm4py.visualization.transition_system import visualizer as ts_visualizer

if __name__ == "__main__":
	gviz = ts_visualizer.apply(ts, parameters={ts_visualizer.Variants.VIEW_BASED.value.Parameters.FORMAT: "svg"})
	ts_visualizer.view(gviz)
```




## Petri Nets with Reset / Inhibitor arcs


The support to Petri nets with reset / inhibitor arcs is provided through
the 
arctype
 property of a 
PetriNet.Arc
 object.
In particular, the 
arctype
 property could assume two different values:
,

- inhibitor
: defines an inhibitor arc. An inhibitor arcs blocks the firing
of all the transitions to which is connected, assuming that there is one token
in the source place.,

- reset
: defines a reset arc. A reset arc sucks all the tokens from its source
place whenever the target transition is fired.
The corresponding semantic, that is identical in signature to the classic semantics of
Petri nets, is defined in 
pm4py.objects.petri_net.inhibitor_reset.semantics
.


## Data Petri nets


Data Petri nets
 include the execution context in the marking object, in such way
that the execution of a transition may depend on the value of this execution context, and not only
on the tokens. Data Petri nets are defined extensively in the following scientific contribution:
Mannhardt, Felix, et al. "Balanced multi-perspective checking of process conformance." Computing 98.4 (2016): 407-437.
The semantics of a data Petri net requires the specification of the execution context (as dictionary associating
to attribute keys some values), and is defined in 
pm4py.objects.petri_net.data_petri_nets.semantics
. In particular, the following
methods require the execution context:,

- semantics.enabled_transitions(pn, m, e)
: checks the enabled transitions in the provided Petri net 
pn
and marking 
m
 when the execution context is updated with the information coming from the current event.,

- semantics.execute(t, pn, m, e)
: executes (whether possible) the transition 
t
 in the marking 
m
where the execution context is updated with the information coming from the current event.
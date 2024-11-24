# BPMN Support

In PM4Py, we offer support for importing, exporting, and layouting BPMN diagrams. The support is limited to the following BPMN elements:

- Events (start/end events)
- Tasks
- Gateways (exclusive, parallel, inclusive)

Moreover, we offer support for conversion to and from some process models implemented in PM4Py (such as Petri nets and BPMN diagrams).

## BPMN 2.0 – Importing

The BPMN 2.0 XML files can be imported using the following instructions:

```python
import pm4py
import os

if __name__ == "__main__":
    bpmn_graph = pm4py.read_bpmn(os.path.join("tests", "input_data", "running-example.bpmn"))
```

## BPMN 2.0 – Exporting

The BPMN models can be exported using the following instructions (here, `bpmn_graph` is the Python object hosting the model).

```python
import pm4py
import os

if __name__ == "__main__":
    pm4py.write_bpmn(bpmn_graph, "ru.bpmn")
```

## BPMN 2.0 – Layouting

A layouting operation tries to give a good position to the nodes and the edges of the BPMN diagram. For our purposes, we chose an octilinear edges layout. The following commands perform the layouting:

```python
from pm4py.objects.bpmn.layout import layouter

if __name__ == "__main__":
    bpmn_graph = layouter.apply(bpmn_graph)
```

## BPMN 2.0 – Conversion to Petri net

A conversion of a BPMN model into a Petri net model enables different PM4Py algorithms (such as conformance checking and simulation algorithms), hence is a particularly important operation. To convert a BPMN model into an (accepting) Petri net, the following code can be used:

```python
import pm4py

if __name__ == "__main__":
    net, im, fm = pm4py.convert_to_petri_net(bpmn_graph)
```

## BPMN 2.0 – Conversion from a Process Tree

Process trees are important classes of block-structured processes (and the output of the inductive miner algorithm). These models can be easily converted to BPMN models. Let’s see an example. First, we import an XES event log, and we discover a model using the inductive miner:

```python
import pm4py
import os

if __name__ == "__main__":
    log = pm4py.read_xes(os.path.join("tests", "input_data", "running-example.xes"))
    log = pm4py.convert_to_event_log(log)
    tree = pm4py.discover_process_tree_inductive(log)
```

Then, we can convert that to a BPMN graph:

```python
import pm4py

if __name__ == "__main__":
    bpmn_graph = pm4py.convert_to_bpmn(tree)
```
# Social Network Analysis

In PM4Py, we offer support for different Social Network Analysis metrics and support for the discovery of roles.

## Handover of Work

The Handover of Work metric measures how many times an individual is followed by another individual in the execution of a business process.
To calculate the Handover of Work metric, the following code could be used:

```python
import pm4py

if __name__ == "__main__":
	hw_values = pm4py.discover_handover_of_work_network(log)
```

Then, a visualization could be obtained through NetworkX or through Pyvis:

```python
import pm4py

if __name__ == "__main__":
	pm4py.view_sna(hw_values)
```

## Subcontracting

The subcontracting metric calculates how many times the work of an individual is interleaved by the work of another individual, only to eventually “return” to the original individual. To measure the subcontracting metric, the following code could be used:

```python
import pm4py

if __name__ == "__main__":
	sub_values = pm4py.discover_subcontracting_network(log)
```

Then, a visualization could be obtained through NetworkX or through Pyvis:

```python
import pm4py

if __name__ == "__main__":
	pm4py.view_sna(sub_values)
```

## Working Together

The Working Together metric calculates how many times two individuals work together to resolve a process instance. To measure the Working Together metric, the following code could be used:

```python
import pm4py

if __name__ == "__main__":
	wt_values = pm4py.discover_working_together_network(log)
```

Then, a visualization could be obtained through NetworkX or through Pyvis:

```python
import pm4py

if __name__ == "__main__":
	pm4py.view_sna(wt_values)
```

## Similar Activities

The Similar Activities metric calculates how similar the work patterns are between two individuals. To measure the Similar Activities metric, the following code could be used:

```python
import pm4py

if __name__ == "__main__":
	ja_values = pm4py.discover_activity_based_resource_similarity(log)
```

Then, a visualization could be obtained through NetworkX or through Pyvis:

```python
import pm4py

if __name__ == "__main__":
	pm4py.view_sna(ja_values)
```

## Roles Discovery

A role is a set of activities in the log that are executed by a similar (multi)set of resources. Hence, it is a specific function within an organization. Grouping the activities into roles can help:

- In understanding which activities are executed by which roles,
- By understanding roles themselves (the numerosity of resources for a single activity may not provide enough explanation).

Initially, each activity corresponds to a different role and is associated with the multiset of its originators. After that, roles are merged according to their similarity until no more merges are possible.
First, you need to import a log:

```python
import pm4py
import os
if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "receipt.xes"))
```

After that, the role detection algorithm can be applied:

```python
import pm4py

if __name__ == "__main__":
	roles = pm4py.discover_organizational_roles(log)
```

We can print the sets of activities that are grouped into roles by doing

print([x[0] for x in roles]).

## Clustering (SNA results)

Given the results of applying an SNA metric, a clustering operation permits grouping the resources that are connected by a meaningful connection in the given metric. For example:

- Clustering the results of the working together metric, individuals that work often together would be inserted into the same group,
- Clustering the results of the similar activities metric, individuals that work on the same tasks would be inserted into the same group.

We provide a baseline method to get a list of groups (where each group is a list of resources) from the specification of the values of an SNA metric. This can be applied as follows on the running-example log and the results of the similar activities metric:

```python
import pm4py
import os

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "running-example.xes"))

	sa_metric = pm4py.discover_activity_based_resource_similarity(log)

	from pm4py.algo.organizational_mining.sna import util
	clustering = util.cluster_affinity_propagation(sa_metric)
```

## Resource Profiles

The profiling of resources from event logs is also possible. We implement the approach described in:
Pika, Anastasiia, et al. "Mining resource profiles from event logs." ACM Transactions on Management Information Systems (TMIS) 8.1 (2017): 1-30.
Basically, the behavior of a resource can be measured over a period of time with different metrics presented in the paper:

- RBI 1.1 (number of distinct activities): Number of distinct activities done by a resource in a given time interval [t1, t2),
- RBI 1.3 (activity frequency): Fraction of completions of a given activity a by a given resource r during a given time slot [t1, t2), with respect to the total number of activity completions by resource r during [t1, t2),
- RBI 2.1 (activity completions): The number of activity instances completed by a given resource during a given time slot,
- RBI 2.2 (case completions): The number of cases completed during a given time slot in which a given resource was involved,
- RBI 2.3 (fraction case completion): The fraction of cases completed during a given time slot in which a given resource was involved with respect to the total number of cases completed during the time slot,
- RBI 2.4 (average workload): The average number of activities started by a given resource but not completed at a moment in time,
- RBI 3.1 (multitasking): The fraction of active time during which a given resource is involved in more than one activity with respect to the resource's active time,
- RBI 4.3 (average duration activity): The average duration of instances of a given activity completed during a given time slot by a given resource,
- RBI 4.4 (average case duration): The average duration of cases completed during a given time slot in which a given resource was involved,
- RBI 5.1 (interaction two resources): The number of cases completed during a given time slot in which two given resources were involved,
- RBI 5.2 (social position): The fraction of resources involved in the same cases with a given resource during a given time slot with respect to the total number of resources active during the time slot.

The following example calculates these metrics starting from the running-example XES event log:

```python
import os
from pm4py.algo.organizational_mining.resource_profiles import algorithm
import pm4py

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "running-example.xes"))
	log = pm4py.convert_to_event_log(log)
	# Metric RBI 1.1: Number of distinct activities done by a resource in a given time interval [t1, t2)
	print(algorithm.distinct_activities(log, "2010-12-30 00:00:00", "2011-01-25 00:00:00", "Sara"))
	# Metric RBI 1.3: Fraction of completions of a given activity a by a given resource r,
	# during a given time slot [t1, t2), with respect to the total number of activity completions by resource r
	# during [t1, t2)
	print(algorithm.activity_frequency(log, "2010-12-30 00:00:00", "2011-01-25 00:00:00", "Sara", "decide"))
	# Metric RBI 2.1: The number of activity instances completed by a given resource during a given time slot.
	print(algorithm.activity_completions(log, "2010-12-30 00:00:00", "2011-01-25 00:00:00", "Sara"))
	# Metric RBI 2.2: The number of cases completed during a given time slot in which a given resource was involved.
	print(algorithm.case_completions(log, "2010-12-30 00:00:00", "2011-01-25 00:00:00", "Pete"))
	# Metric RBI 2.3: The fraction of cases completed during a given time slot in which a given resource was involved
	# with respect to the total number of cases completed during the time slot.
	print(algorithm.fraction_case_completions(log, "2010-12-30 00:00:00", "2011-01-25 00:00:00", "Pete"))
	# Metric RBI 2.4: The average number of activities started by a given resource but not completed at a moment in time.
	print(algorithm.average_workload(log, "2010-12-30 00:00:00", "2011-01-15 00:00:00", "Mike"))
	# Metric RBI 3.1: The fraction of active time during which a given resource is involved in more than one activity
	# with respect to the resource's active time.
	print(algorithm.multitasking(log, "2010-12-30 00:00:00", "2011-01-25 00:00:00", "Mike"))
	# Metric RBI 4.3: The average duration of instances of a given activity completed during a given time slot by
	# a given resource.
	print(algorithm.average_duration_activity(log, "2010-12-30 00:00:00", "2011-01-25 00:00:00", "Sue", "examine thoroughly"))
	# Metric RBI 4.4: The average duration of cases completed during a given time slot in which a given resource was involved.
	print(algorithm.average_case_duration(log, "2010-12-30 00:00:00", "2011-01-25 00:00:00", "Sue"))
	# Metric RBI 5.1: The number of cases completed during a given time slot in which two given resources were involved.
	print(algorithm.interaction_two_resources(log, "2010-12-30 00:00:00", "2011-01-25 00:00:00", "Mike", "Pete"))
	# Metric RBI 5.2: The fraction of resources involved in the same cases with a given resource during a given time slot
	# with respect to the total number of resources active during the time slot.
	print(algorithm.social_position(log, "2010-12-30 00:00:00", "2011-01-25 00:00:00", "Sue"))
```

## Organizational Mining

With event logs, we are able to identify groups of resources doing similar activities. As we have seen in the previous sections, we have different ways to detect these groups automatically from event logs:

- Discovering the Similar Activities metric and applying a clustering algorithm to find the groups,
- Applying the roles discovery algorithm (Burattin et al.).

As a third option, an attribute might be present in the events describing the group that performed the event.

With the term "organizational mining," we mean the discovery of behavior-related information specific to an organizational group (e.g., which activities are done by the group).

We provide an implementation of the approach described in:
Yang, Jing, et al. "OrgMining 2.0: A Novel Framework for Organizational Model Mining from Event Logs." arXiv preprint arXiv:2011.12445 (2020).

The approach provides descriptions of some group-related metrics (local diagnostics). Among these, we have:

- **Group Relative Focus**: (on a given type of work) specifies how much a resource group performed this type of work compared to the overall workload of the group. It can be used to measure how the workload of a resource group is distributed over different types of work, i.e., work diversification of the group.
  
- **Group Relative Stake**: (in a given type of work) specifies how much this type of work was performed by a certain resource group among all groups. It can be used to measure how the workload devoted to a certain type of work is distributed over resource groups in an organizational model, i.e., work participation by different groups.
  
- **Group Coverage**: with respect to a given type of work, specifies the proportion of members of a resource group that performed this type of work.
  
- **Group Member Contribution**: of a member of a resource group with respect to a given type of work specifies how much of this type of work by the group was performed by the member. It can be used to measure how the workload of the entire group devoted to a certain type of work is distributed over the group members.

The following example calculates these metrics starting from the receipt XES event log and shows how the information can be exploited, using an attribute that specifies which group is doing the task:

```python
import pm4py
import os
from pm4py.algo.organizational_mining.local_diagnostics import algorithm as local_diagnostics

if __name__ == "__main__":
	log = pm4py.read_xes(os.path.join("tests", "input_data", "receipt.xes"))
	log = pm4py.convert_to_event_log(log)
	# This applies the organizational mining from an attribute that is in each event, describing the group that is performing the task.
	ld = local_diagnostics.apply_from_group_attribute(log, parameters={local_diagnostics.Parameters.GROUP_KEY: "org:group"})
	# GROUP RELATIVE FOCUS (on a given type of work) specifies how much a resource group performed this type of work
	# compared to the overall workload of the group. It can be used to measure how the workload of a resource group
	# is distributed over different types of work, i.e., work diversification of the group.
	print("\ngroup_relative_focus")
	print(ld["group_relative_focus"])
	# GROUP RELATIVE STAKE (in a given type of work) specifies how much this type of work was performed by a certain
	# resource group among all groups. It can be used to measure how the workload devoted to a certain type of work is
	# distributed over resource groups in an organizational model, i.e., work participation by different groups.
	print("\ngroup_relative_stake")
	print(ld["group_relative_stake"])
	# GROUP COVERAGE with respect to a given type of work specifies the proportion of members of a resource group that
	# performed this type of work.
	print("\ngroup_coverage")
	print(ld["group_coverage"])
	# GROUP MEMBER CONTRIBUTION of a member of a resource group with respect to a given type of work specifies how
	# much of this type of work by the group was performed by the member. It can be used to measure how the workload
	# of the entire group devoted to a certain type of work is distributed over the group members.
	print("\ngroup_member_contribution")
	print(ld["group_member_contribution"])
```

Alternatively, the `apply_from_clustering_or_roles` method of the same class can be used, providing the log as the first argument and the results of the clustering as the second argument.

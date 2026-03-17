'''
    PM4Py – A Process Mining Library for Python
Copyright (C) 2026 Process Intelligence Solutions UG (haftungsbeschränkt)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see this software project's root or
visit <https://www.gnu.org/licenses/>.

Website: https://processintelligence.solutions
Contact: info@processintelligence.solutions
'''
# Author: Maximilian Josef Frank (https://orcid.org/0000-0002-0714-7748)

import random
import itertools

# typing
from typing import Dict, FrozenSet, Iterable, List, Set, Tuple, Union
TransitionMap = Dict[str, List[FrozenSet[str]]]
InputMap = OutputMap = TransitionMap
Individual = Tuple[InputMap, OutputMap]

class iset(frozenset):
    "Indexable frozenset printing as set, i.e. without `frozenset(…)`"
    def __repr__(self):
        return "{" + repr(sorted(self))[1:-1] + "}"

    @staticmethod
    def flat(item: Iterable) -> "iset":
        return iset(itertools.chain(*item))

def rand_partition(pool: Iterable) -> List[Union[Set[str], FrozenSet[str]]]:
    pool = set(pool)
    #     also ensures no activity in two partitions
    #     s. 4. Causal Matrix, Def. 4; https://doi.org/10.1007/11494744_5
    partition = []
    while pool:
        draw = iset(random.sample(
            tuple(pool),
            random.randint(1, len(pool))
        ))
        partition.append(draw)
        pool -= draw
    return partition

def add_singleton_partition(tmap: TransitionMap, key: str, t: str):
    partitions = tmap.setdefault(key, []) # tmap[key] or []
    if not any(t in partition for partition in partitions):
        partitions.append(iset({t}))

def remove_transition_from_partitions(tmap: TransitionMap, key: str, t: str):
    partitions = tmap.setdefault(key, []) # tmap[key] or []
    for i,partition in enumerate(partitions):
        if t in partition:
            updated = iset(partition - {t})
            if updated:
                partitions[i] = updated
            else:
                del partitions[i]
            return

def get_src_sink_sets_for_wfnet(I: InputMap, O: OutputMap, T: List[str]) -> Tuple[List[str], List[str]]:
    """Determines input set and output set, which need to be connected by a place to create a WF-net"""
    def add2graphs(graphs, t, nextT):
        # find graph
        graph = next((g for g in graphs if t in g), None)
        if graph is None:
            graph = [t]
            graphs.append(graph)
        # append plain/grouped T
        successors = []
        for S in nextT[t]:
            if type(S) == str:
                successors.append(S)
            else:
                successors.extend(S)
        graph += successors
        # merge if path end = start
        for tn in successors: # tn = end
            for g2 in graphs[:]: # [:] = copy
                if g2[0] == tn and g2 != graph:
                    graph += g2
                    graphs.remove(g2)
                    break
        return graphs
    graphsI, graphsO = [], []
    for t in T:
        graphsI = add2graphs(graphsI, t, I)
        graphsO = add2graphs(graphsO, t, O)
    sources = [g[0] for g in graphsO] # ⋃sources = ∀t reachable from O[∀sources]
    sinks = [g[0] for g in graphsI] # ⋃sinks = ∀t reachable from I[∀sinks]
    return sources, sinks

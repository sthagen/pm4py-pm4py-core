'''
    PM4Py â€“ A Process Mining Library for Python
Copyright (C) 2024 Process Intelligence Solutions UG (haftungsbeschrÃ¤nkt)

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

from collections import defaultdict
import copy
import itertools

from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils


def apply(genetic_matrix, parameters=None):
    """
    Converts a Genetic matrix to a Petri net

    Reference paper:
    Maximilian Josef Frank. "Optimising and Implementing the Genetic Miner in PM4Py" (2026).

    Parameters
    --------------
    genetic_matrix
        Genetic matrix
    parameters
        (Unused) Possible parameters of the algorithm

    Returns
    --------------
    net
        Petri net
    im
        Initial marking
    fm
        Final marking
    """
    # import here to resolve circular import dependencies
    from pm4py.algo.discovery.genetic.util import get_src_sink_sets_for_wfnet, iset
    I = genetic_matrix.input_map
    O = genetic_matrix.output_map
    T = genetic_matrix.transitions
    # @src 5.3. Sophisticated Mapping, Def. 7; https://doi.org/10.1007/11494744_5
    # original, but insanely inefficient (for |A|=23, |P(A)|=8388608):
    #    X = {(Ti, To) ∈ P(A) × P(A) | ∀t∈Ti To ∈ O(t) ∧ ∀t∈To Ti ∈ I(t)}
    # equivalent and more efficient (for |A|=23, |I(∀t)×O(∀t)|=24×16=384):
    #    X = {(Ti, To) ∈ I(∀t) × O(∀t) | ∀t∈Ti To ∈ O(t) ∧ ∀t∈To Ti ∈ I(t)}
    X = list(filter( # if no list(), X gets consumed as stream
        lambda Tio: # = (Ti, To)
            all(Tio[1] in O[t] for t in Tio[0]) and
            all(Tio[0] in I[t] for t in Tio[1]),
            # holds s. Def 4, constraint 3+4; https://doi.org/10.1007/11494744_5
        itertools.product(
            iset.flat(I.values()),
            iset.flat(O.values())
        )
    ))
    Xs = list(itertools.chain( # Xs = non-sophisticated / silent-transition places
        [ (Si,iset([t])) for Ti,t in zip(I.values(), I.keys()) for Si in Ti],
        [ (iset([t]),So) for t,To in zip(O.keys(), O.values()) for So in To]
    ))
    # remove places in Xs which are fully covered by X
    Xs = [ Tio for Tio in Xs if not any(
        Tio[0] <= Ti and Tio[1] <= To for Ti,To in X
    )]
    # remove Xs (silent transitions from non-simple matrix) from X (s. later)
    def is_transitively_not_sophisticated(Tio, places):
        """If place `Tio` is not in sophisticated mapping (i.e. place in `Xs`), all adjacent places (i.e. with same input/output transition) are replaced by non-sophisticated places and their silent transitions."""
        return any(
            len(Ti & Tio[0]) or len(To & Tio[1]) # & = intersect
            for Ti,To in places
        )
    check = copy.copy(X)
    while check:
        Tio = check.pop(0)
        if is_transitively_not_sophisticated(Tio, Xs):
            Xs.append(Tio)
            X.remove(Tio)
            for Tio2 in X:
                if Tio2 not in check and is_transitively_not_sophisticated(Tio2, Xs):
                    check.append(Tio2)
    # build PetriNet
    io = [PetriNet.Place('i'), PetriNet.Place('o')]
    net = PetriNet()
    net.places.update(PetriNet.Place(p) for p in map(str, X))
    net.places.update(io)
    # Non-silent transitions must have a label; label=None is rendered as invisible.
    net.transitions.update(PetriNet.Transition(t, t) for t in T)
    # original: F = {(i,t) | t∈T ∧ •t=∅} ∪ {(t,o) | t∈T ∧ t•=∅} ∪ …
    T_noI, T_noO = get_src_sink_sets_for_wfnet(I, O, T)
    arcs_pt = [ ('i', t) for t in T_noI ] + [
        ((Ti,To), t) for (Ti,To),t in itertools.product(X, T) if t in To
    ]
    arcs_tp = [ (t, 'o') for t in T_noO ] + [
        (t, (Ti,To)) for t,(Ti,To) in itertools.product(T, X) if t in Ti
    ]
    # convert to instances
    getPlace = lambda name: next(filter(lambda p: p.name == name, net.places), None)
    getTransition = lambda name: next(filter(lambda t: t.name == name, net.transitions), None)
    arcs_pt = [(getPlace(str(p)), getTransition(t)) for p,t in arcs_pt]
    arcs_tp = [(getTransition(t), getPlace(str(p))) for t,p in arcs_tp]
    # add instance arcs
    for i,o in itertools.chain(arcs_pt, arcs_tp):
        petri_utils.add_arc_from_to(i, o, net)
    # if causal matrix not simple (Def. 8; https://doi.org/10.1007/11494744_5):
    # @src 5.2. Naive Mapping, Def. 6; https://doi.org/10.1007/11494744_5
    # add incoming/outgoing silent places
    Ti = set(itertools.chain(*(Ti for Ti,_ in Xs)))
    To = set(itertools.chain(*(To for _,To in Xs)))
    Ps_o = { name : PetriNet.Place("o"+str(name))    # output of prev non-silent T
        for name in [ (t,s) for t in Ti for s in O[t] ]
    }
    Ps_i = { name : PetriNet.Place("i"+str(name))    # input of next non-silent T
        for name in [ (t,s) for t in To for s in I[t] ]
    }
    net.places.update(itertools.chain(Ps_o.values(), Ps_i.values()))
    Ts = defaultdict(lambda: PetriNet.Transition(name="")) # name="" → silent
    # add arcs
    for (t1,So),p in Ps_o.items():
        petri_utils.add_arc_from_to(getTransition(t1), p, net)
        for t2 in So: # connect silent T
            petri_utils.add_arc_from_to(p, Ts[t1,t2], net)
    for (t2,Si),p in Ps_i.items():
        petri_utils.add_arc_from_to(p, getTransition(t2), net)
        for t1 in Si: # connect silent T
            petri_utils.add_arc_from_to(Ts[t1,t2], p, net)
    net.transitions.update(Ts.values())
    # add markings
    markings = [Marking() for _ in io]
    for m,p in zip(markings, io):
        m[p] = 1
    return (net, *markings)

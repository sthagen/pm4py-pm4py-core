'''
    PM4Py – A Process Mining Library for Python
Copyright (C) 2024 Process Intelligence Solutions UG (haftungsbeschränkt)

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

from pm4py.util.lp import solver
from pm4py.util import constants
from pm4py.objects.petri_net.utils.petri_utils import remove_place
from typing import Tuple
import warnings
import importlib.util
from pm4py.objects.petri_net.obj import PetriNet, Marking


def apply_reduction(
    net: PetriNet, im: Marking, fm: Marking
) -> Tuple[PetriNet, Marking, Marking]:
    """
    Apply the Murata reduction to an accepting Petri net, removing structurally redundant (implicit) places.

    This implementation follows the (Berthelot) implicit-place check by searching, via ILP,
    for a place-flow f = a_p * p - Σ a_q * q (a_p >= 1, a_q >= 0) such that:

      (1) f is a P-invariant (flow):  a_p*C(p,t) - Σ a_q*C(q,t) = 0    for all transitions t
          where C(p,t) = Post(p,t) - Pre(p,t)

      (2) a_p*Pre(p,t) - Σ a_q*Pre(q,t) <= k   for all transitions t
          with k = a_p*M0(p) - Σ a_q*M0(q),  and k >= 0

    If such a solution exists, the candidate place is implicit and can be removed without changing behavior.

    Parameters
    ---------------
    net
        Petri net
    im
        Initial marking
    fm
        Final marking

    Returns
    --------------
    net
        Reduced Petri net
    im
        Initial marking (unchanged)
    fm
        Final marking (unchanged)
    """
    places = sorted(list(net.places), key=lambda x: x.name)
    redundant = set()

    # Choose solver backend
    proposed_solver = solver.SCIPY
    if importlib.util.find_spec("pulp"):
        proposed_solver = solver.PULP
    else:
        if constants.SHOW_INTERNAL_WARNINGS:
            warnings.warn(
                "solution from scipy may be unstable. Please install PuLP (pip install pulp) for fully reliable results."
            )

    for place in places:
        # Skip already proven redundant places
        if place in redundant:
            continue

        # Skip places in the initial or final markings
        if place in im or place in fm:
            continue

        # Work on the "current" net as if previously found redundant places were removed:
        active_places = [p for p in places if p not in redundant]
        active_places = sorted(active_places, key=lambda x: x.name)
        place_index = {p: i for i, p in enumerate(active_places)}

        n_places = len(active_places)
        n_vars = n_places + 1  # last variable is k
        k_idx = n_vars - 1

        Aeq = []
        Aub = []
        beq = []
        bub = []

        # ---------------------------------------------------------------------
        # (A) k = a_p*M0(p) - Σ a_q*M0(q)
        #     => a_p*M0(p) - Σ a_q*M0(q) - k = 0
        # ---------------------------------------------------------------------
        eq = [0] * n_vars
        for p2 in active_places:
            m0 = im[p2] if p2 in im else 0
            if m0 == 0:
                continue
            if p2 == place:
                eq[place_index[p2]] += m0
            else:
                eq[place_index[p2]] -= m0
        eq[k_idx] = -1
        Aeq.append(eq)
        beq.append(0)

        # ---------------------------------------------------------------------
        # (B) Flow constraints: for all transitions t,
        #     a_p*C(p,t) - Σ a_q*C(q,t) = 0
        #     where C(p,t)=Post(p,t)-Pre(p,t)
        # ---------------------------------------------------------------------
        for trans in net.transitions:
            pre = {}
            post = {}

            for arc in trans.in_arcs:
                src = arc.source
                if src in place_index:
                    pre[src] = pre.get(src, 0) + arc.weight

            for arc in trans.out_arcs:
                tgt = arc.target
                if tgt in place_index:
                    post[tgt] = post.get(tgt, 0) + arc.weight

            eq = [0] * n_vars
            for p2 in active_places:
                c_val = post.get(p2, 0) - pre.get(p2, 0)
                if c_val == 0:
                    continue
                if p2 == place:
                    eq[place_index[p2]] += c_val
                else:
                    eq[place_index[p2]] -= c_val
            # k has coefficient 0 here
            Aeq.append(eq)
            beq.append(0)

        # ---------------------------------------------------------------------
        # (C) Implicitness inequalities: for all transitions t,
        #     a_p*Pre(p,t) - Σ a_q*Pre(q,t) - k <= 0
        # ---------------------------------------------------------------------
        for trans in net.transitions:
            ineq = [0] * n_vars
            for arc in trans.in_arcs:
                p2 = arc.source
                if p2 not in place_index:
                    continue
                if p2 == place:
                    ineq[place_index[p2]] += arc.weight
                else:
                    ineq[place_index[p2]] -= arc.weight
            ineq[k_idx] = -1
            Aub.append(ineq)
            bub.append(0)

        # ---------------------------------------------------------------------
        # (D) Variable lower bounds:
        #     a_p >= 1, a_q >= 0, k >= 0
        #     Implemented as -a <= b
        # ---------------------------------------------------------------------
        for p2 in active_places:
            ineq = [0] * n_vars
            ineq[place_index[p2]] = -1
            Aub.append(ineq)
            if p2 == place:
                bub.append(-1)  # -a_p <= -1  -> a_p >= 1
            else:
                bub.append(0)   # -a_q <= 0   -> a_q >= 0

        ineq = [0] * n_vars
        ineq[k_idx] = -1
        Aub.append(ineq)
        bub.append(0)  # -k <= 0 -> k >= 0

        # Objective (any feasible solution is enough; minimize sum to keep it small)
        c = [1] * n_vars
        integrality = [1] * n_vars

        xx = solver.apply(
            c,
            Aub,
            bub,
            Aeq,
            beq,
            variant=proposed_solver,
            parameters={"integrality": integrality},
        )

        if (hasattr(xx, "success") and xx.success) or (
            hasattr(xx, "sol_status") and xx.sol_status > -1
        ):
            redundant.add(place)

    # Remove redundant places (deterministic order)
    for pl in sorted(list(redundant), key=lambda x: x.name):
        net = remove_place(net, pl)

    return net, im, fm

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
# Author: Maximilian Josef Frank (https://orcid.org/0000-0002-0714-7748)

from collections import defaultdict
import copy
import csv
from datetime import datetime
from pm4py.util.timeout import func_timeout, FunctionTimedOut
import numpy
import random
import itertools

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable=None, *args, **kwargs):
        return iterable if iterable is not None else []

import pm4py
from pm4py.util import exec_utils, constants
from pm4py.util import xes_constants as xes
from pm4py.algo.discovery.genetic.algorithm import Parameters
from pm4py.objects.conversion.log import converter as log_converter
from pm4py.objects.conversion.genetic_matrix.variants.to_petri_net import apply as matrix2petrinet
from pm4py.algo.discovery.genetic.util import get_src_sink_sets_for_wfnet, iset, rand_partition
from pm4py.objects.genetic_matrix.obj import GeneticMatrix

# typing
from typing import Any, Dict, Iterable, List, Optional, TextIO, Tuple, Union
from pandas.core.frame import DataFrame
from pm4py.objects.log.obj import EventLog, EventStream
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.algo.discovery.genetic.util import InputMap, OutputMap, Individual
from pm4py.utils import is_polars_lazyframe


def apply(
    log: Union[EventLog, EventStream, DataFrame],
    parameters: Optional[Dict[Union[str, Parameters], Any]] = None,
) -> Tuple[PetriNet, Marking, Marking]:
    """
    Discovers a Petri net using Genetic Miner

    Reference paper:
    Maximilian Josef Frank. "Optimising and Implementing the Genetic Miner in PM4Py" (2026).

    Parameters
    ------------
    log
        Event log
    parameters
        Possible parameters of the algorithm,
        including:
            - Parameters.ACTIVITY_KEY
            - Parameters.TIMESTAMP_KEY
            - Parameters.CASE_ID_KEY
            - Parameters.POPULATION_SIZE
            - Parameters.ELITISM_RATE
            - Parameters.CROSSOVER_RATE
            - Parameters.MUTATION_RATE
            - Parameters.GENERATIONS
            - Parameters.ELITISM_MIN_SAMPLE
            - Parameters.TOURNAMENT_TIMEOUT
            - Parameters.LOG_CSV

    Returns
    ------------
    net
        Petri net
    im
        Initial marking
    fm
        Final marking
    """
    if parameters is None:
        parameters = {}
    if is_polars_lazyframe(log):
        log = log.collect().to_pandas()
    if not isinstance(log, DataFrame):
        log = log_converter.apply(
            log,
            variant=log_converter.Variants.TO_DATA_FRAME,
            parameters=parameters,
        )

    activity_key = exec_utils.get_param_value(
        Parameters.ACTIVITY_KEY, parameters, xes.DEFAULT_NAME_KEY
    )
    timestamp_key = exec_utils.get_param_value(
        Parameters.TIMESTAMP_KEY, parameters, xes.DEFAULT_TIMESTAMP_KEY
    )
    case_id_key = exec_utils.get_param_value(
        Parameters.CASE_ID_KEY, parameters, constants.CASE_CONCEPT_NAME
    )

    population_size = exec_utils.get_param_value(
        Parameters.POPULATION_SIZE, parameters, 500
    )
    elitism_rate = exec_utils.get_param_value(
        Parameters.ELITISM_RATE, parameters, 0.01
    )
    crossover_rate = exec_utils.get_param_value(
        Parameters.CROSSOVER_RATE, parameters, 1.0
    )
    mutation_rate = exec_utils.get_param_value(
        Parameters.MUTATION_RATE, parameters, 0.01
    )
    generations = exec_utils.get_param_value(
        Parameters.GENERATIONS, parameters, 100
    )
    elitism_min_sample = exec_utils.get_param_value(
        Parameters.ELITISM_MIN_SAMPLE, parameters, 5
    )
    tournament_timeout = exec_utils.get_param_value(
        Parameters.TOURNAMENT_TIMEOUT, parameters, None
    )
    log_csv = exec_utils.get_param_value(
        Parameters.LOG_CSV, parameters, None
    )

    # configure parameters
    if population_size < 2:
        raise ValueError("population_size < 2: You need at least two parents for each next generation, thus at least a population size of 2.")
    if elitism_min_sample >= population_size:
        elitism_min_sample = population_size - 1
    if elitism_min_sample < 1:
        raise ValueError("elitism_min_sample < 1: No empty samples allowed.")
    if log_csv:
        log_csv = csv.writer(log_csv)
        log_csv.writerow(['timestamp', 'generation'] + [f'fitness{i}' for i in range(population_size)])
    # @src 6.3. Genetic Operations; https://doi.org/10.1007/11494744_5
    T = tuple(log[activity_key].unique())
    if tournament_timeout is None or tournament_timeout < 1:
        tournament_timeout = 3 * len(T) * log.shape[0] * (46 / 1202267 / 26)
        # based on previous runs: 46s for 1202267 traces with 26 activities
    if tournament_timeout < 1:
        tournament_timeout = 1
    history = []
    best_individual = None
    best_fitness = -1.0
    population = individuals(log, population_size, T, { # [(I,O), …]
        "activity_key":activity_key, "timestamp_key":timestamp_key, "case_id_key":case_id_key
    })
    for _ in tqdm(range(generations), "Genetic generations"):
        population, fitness = tournament(
            tqdm(population, f"└─Tournament {len(history)}"),
            log,
            T,
            sort=True,
            timeout=tournament_timeout,
            activity_key=activity_key,
            timestamp_key=timestamp_key,
            case_id_key=case_id_key,
        )
        if fitness[0] > best_fitness:
            best_fitness = fitness[0]
            best_individual = copy.deepcopy(population[0])
        if log_csv:
            log_csv.writerow([datetime.now(), len(history)] + fitness)
        if fitness[0] == 1 or (history and all(f == fitness[0] for f in history[-int(generations/2):])):
            break
        history.append(fitness[0])
        # elitism
        next_population = population[:round(elitism_rate * population_size)]
        # fill with offsprings
        while len(next_population) < population_size:
            parent1, parent2 = sample_parents(population, fitness, elitism_min_sample)
            if random.random() < crossover_rate:
                offsprings = crossover(parent1, parent2, T)
            else:
                offsprings = copy.deepcopy((parent1, parent2))
            for offspring in offsprings:
                if len(next_population) < population_size:
                    offspring = mutate(offspring, mutation_rate)
                    next_population.append(offspring)
        population = next_population
    if best_individual is None:
        population, fitness = tournament(
            population,
            log,
            T,
            sort=True,
            timeout=tournament_timeout,
            activity_key=activity_key,
            timestamp_key=timestamp_key,
            case_id_key=case_id_key,
        )
        best_individual = copy.deepcopy(population[0])
    return matrix2petrinet(GeneticMatrix(*best_individual, T))

def individuals(log: Union[DataFrame, EventLog], sample_size=1, T=None, keys: Dict[str, str] = {"activity_key":xes.DEFAULT_NAME_KEY, "timestamp_key":xes.DEFAULT_TIMESTAMP_KEY, "case_id_key":constants.CASE_CONCEPT_NAME}) -> List[Individual]:
    if not T:
        T = tuple(log[keys['activity_key']].unique())
    T_idx = {activity: idx for idx, activity in enumerate(T)}
    # @src 6.1. Initial Population; https://doi.org/10.1007/11494744_5
    # create matrix C
    C = numpy.zeros((len(T), len(T)))
    for _,group in tqdm(log.sort_values(keys['timestamp_key'], ascending=True).groupby(keys['case_id_key']), desc="Find consecutive activities"):
        prev_activity = None
        for _, row in group.iterrows():
            activity = row[keys['activity_key']]
            if prev_activity is not None:
                C[T_idx[prev_activity], T_idx[activity]] += 1
            prev_activity = activity
    row_sums = C.sum(axis=1, keepdims=True)
    Cn = numpy.divide(C, row_sums, out=numpy.zeros_like(C, dtype=float), where=row_sums != 0)
    samples = []
    for _ in tqdm(range(sample_size), "Initial population"):
        I,O = defaultdict(list), defaultdict(list)
        for i,o in numpy.ndindex(C.shape):
            if random.random() < Cn[i,o]:    # [0,1[ < [0,1]; 0 < 0 = false
                O[T[i]].append(T[o])
                I[T[o]].append(T[i])
        I,O = repair(I, O, C, T)
        # partitioning already ensures no T in >1 partitions
        # s. 4. Causal Matrix, Def. 4; https://doi.org/10.1007/11494744_5
        for i in I.keys():
            I[i] = rand_partition(I[i])
        for o in O.keys():
            O[o] = rand_partition(O[o])
        samples.append((I,O))
    return samples

def tournament(
    population: List[Individual],
    log: Union[DataFrame, EventLog],
    T,
    sort=True,
    timeout=1,
    *,
    activity_key: str = xes.DEFAULT_NAME_KEY,
    timestamp_key: str = xes.DEFAULT_TIMESTAMP_KEY,
    case_id_key: str = constants.CASE_CONCEPT_NAME,
) -> Tuple[List[Individual], List[float]]:
    """sort=True: sort descending by fitness (i.e. best first)"""
    # @src 6.2. Fitness Calculation; https://doi.org/10.1007/11494744_5
    fitness = []
    for i,(I,O) in enumerate(population):
        model = matrix2petrinet(GeneticMatrix(I,O,T))
        try:
            metrics = func_timeout(
                timeout = timeout,
                func = pm4py.fitness_token_based_replay,
                args = (log, *model),
                kwargs = {
                    "activity_key": activity_key,
                    "timestamp_key": timestamp_key,
                    "case_id_key": case_id_key,
                },
            )
        except FunctionTimedOut:
            print("\tTimeout for individual", i)
            metrics = defaultdict(lambda: 0)
        fitness.append(
            0.4 * metrics['average_trace_fitness']
            # @see https://pm4py-source.readthedocs.io/en/stable/_modules/pm4py/algo/evaluation/replay_fitness/variants/token_replay.html#evaluate
            # average_fitness = sum_fitness / #traces
            # = ∑ fitness per trace / #traces
            #   ∑ fitness per trace * len(log)/#traces
            # = ––––––––––––––––––––––––––––––––––––––
            #        #traces * len(log)/#traces
            #   ∑ fitness per row in log   ∑ fitness per activity
            # = –––––––––––––––––––––––– = ––––––––––––––––––––––
            #           len(log)                 len(log)
            +
            0.6 * metrics['percentage_of_fitting_traces']/100
        )
    if sort:
        population, fitness = zip(*sorted(
            zip(population, fitness),
            key=lambda obj: obj[1],
            reverse=True
        ))
        population, fitness = list(population), list(fitness)
    return (population, fitness)

def sample_parents(population: List[Individual], fitness: List[float], elitism_min_sample: int):
    population_fitness = tuple(zip(population, fitness))
    parent1 = sorted(
        random.sample(population_fitness, k=elitism_min_sample),
        key=lambda obj: obj[1],
        reverse=True
    )[0][0]
    parent2 = sorted(
        random.sample(
            [(i,f) for i,f in population_fitness if i!=parent1],
            k=elitism_min_sample
        ),
        key=lambda obj: obj[1],
        reverse=True
    )[0][0]
    return (parent1, parent2)

def crossover(parent1: Individual, parent2: Individual, T: List[str]) -> Tuple[Individual, Individual]:
    # @src 6.3. Genetic Operations: Crossover; https://doi.org/10.1007/11494744_5
    # 1. cross-over point
    t = random.choice(T)
    # 2. clone parents
    I1,O1 = offspring1 = copy.deepcopy(parent1)
    I2,O2 = offspring2 = copy.deepcopy(parent2)
    # 3. swap and recombine
    if I1[t] and I2[t]:
        old_I1 = iset.flat(I1[t])
        old_I2 = iset.flat(I2[t])
        swap_point = random.randrange(min(len(I1[t]), len(I2[t])))
        toI1, toI2 = I2[t][swap_point:], I1[t][swap_point:]
        # no T can exist twice in I/O[t], s. Def. 4; https://doi.org/10.1007/11494744_5
        # COPY of I_i, else not properly removed in opposite I_j
        I1_flat = iset.flat(I1[t][:swap_point])
        toI1_dedup = [iset(S - I1_flat) for S in toI1 if S - I1_flat]
        I2_flat = iset.flat(I2[t][:swap_point])
        toI2_dedup = [iset(S - I2_flat) for S in toI2 if S - I2_flat]
        # merge
        I1[t], I2[t] = I1[t][:swap_point] + toI1_dedup, I2[t][:swap_point] + toI2_dedup
        new_I1 = iset.flat(I1[t])
        new_I2 = iset.flat(I2[t])
        for c in new_I1 - old_I1:
            _add_singleton_partition(O1, c, t)
        for c in old_I1 - new_I1:
            _remove_value_from_partitions(O1, c, t)
        for c in new_I2 - old_I2:
            _add_singleton_partition(O2, c, t)
        for c in old_I2 - new_I2:
            _remove_value_from_partitions(O2, c, t)
    if O1[t] and O2[t]:
        old_O1 = iset.flat(O1[t])
        old_O2 = iset.flat(O2[t])
        swap_point = random.randrange(min(len(O1[t]), len(O2[t])))
        toO1, toO2 = O2[t][swap_point:], O1[t][swap_point:]
        # no T can exist twice in I/O[t], s. Def. 4; https://doi.org/10.1007/11494744_5
        # COPY of I_i, else not properly removed in opposite I_j
        O1_flat = iset.flat(O1[t][:swap_point])
        toO1_dedup = [iset(S - O1_flat) for S in toO1 if S - O1_flat]
        O2_flat = iset.flat(O2[t][:swap_point])
        toO2_dedup = [iset(S - O2_flat) for S in toO2 if S - O2_flat]
        # merge
        O1[t], O2[t] = O1[t][:swap_point] + toO1_dedup, O2[t][:swap_point] + toO2_dedup
        new_O1 = iset.flat(O1[t])
        new_O2 = iset.flat(O2[t])
        for c in new_O1 - old_O1:
            _add_singleton_partition(I1, c, t)
        for c in old_O1 - new_O1:
            _remove_value_from_partitions(I1, c, t)
        for c in new_O2 - old_O2:
            _add_singleton_partition(I2, c, t)
        for c in old_O2 - new_O2:
            _remove_value_from_partitions(I2, c, t)
    return (offspring1, offspring2)


def _add_singleton_partition(mapping: Dict[str, List[iset]], key: str, value: str) -> None:
    partitions = mapping.setdefault(key, [])
    if any(value in partition for partition in partitions):
        return
    partitions.append(iset({value}))


def _remove_value_from_partitions(mapping: Dict[str, List[iset]], key: str, value: str) -> None:
    partitions = mapping.setdefault(key, [])
    for index, partition in enumerate(partitions):
        if value in partition:
            updated = iset(partition - {value})
            if updated:
                partitions[index] = updated
            else:
                del partitions[index]
            return

def mutate(individual: Individual, rate: float = 0.01) -> Individual:
    # @src 6.3. Genetic Operations: Mutation; https://doi.org/10.1007/11494744_5
    I,O = individual
    for t in I.keys():
        if random.random() < rate:
            I[t] = rand_partition(itertools.chain(*I[t]))
    for t in O.keys():
        if random.random() < rate:
            O[t] = rand_partition(itertools.chain(*O[t]))
    return (I,O)

def repair(I: InputMap, O: OutputMap, C: numpy.ndarray, T: List[str]) -> Individual:
    """
    Merging partitions until petri-net is (coherent) workflow net
    s. last requirement in 4. Causal Matrix, Def. 4; https://doi.org/10.1007/11494744_5
    """
    # WF-Net Definition: each node on path from i to o
    #   → re-connect partitions of each I and O, not I and O together
    left = set(T)
    partitions = []
    while left:
        partition = set()
        Tn = {left.pop()}
        while Tn:
            t = Tn.pop() # also removes from Tn
            left.discard(t) # remove without Exception (s. initial Tn)
            partition.add(t)
            Tn |= (set(I[t]) | set(O[t])) & left
        partitions.append(partition)
    T_idx = {activity: idx for idx, activity in enumerate(T)}

    def rand_connect_one(I: InputMap, O: OutputMap, Ti: Iterable[str], To: Iterable[str], C: numpy.ndarray) -> Individual:
        comb = tuple(itertools.product(Ti, To))
        try:
            ti,to = random.choices(
                comb,
                weights = [ C[T_idx[ti], T_idx[to]] for ti,to in comb ],
                k=1
            )[0]
        except ValueError:
            ti,to = random.choice(comb)
        O[ti].append(to)
        I[to].append(ti)
        return I,O
    while len(partitions) > 1:
        random.shuffle(partitions)
        # merge Ti / To of partition to other partition
        first, last = get_src_sink_sets_for_wfnet(I, O, partitions[1])
        for i in first:
            # connect any→i
            I,O = rand_connect_one(I, O, [i], partitions[0], C)
        for o in last:
            # connect o→any
            I,O = rand_connect_one(I, O, partitions[0], [o], C)
        # pop first + merge with new first (i.e. old second)
        merging = partitions.pop(0)
        partitions[0] |= merging
    return (I,O)

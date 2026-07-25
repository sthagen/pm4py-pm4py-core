import datetime
import importlib
import importlib.util
import importlib.machinery
import os
import sys
import tempfile
import types
import unittest
from collections import Counter
from contextlib import ExitStack
from unittest import mock

import pandas as pd

import pm4py
from pm4py.algo.clustering.profiles.variants import sklearn_profiles
from pm4py.algo.discovery.inductive.dtypes.im_ds import IMDataStructureUVCL
from pm4py.algo.discovery.powl.inductive.variants.dynamic_clustering import (
    dynamic_clustering_partial_order_cut as dynamic_cut,
)
from pm4py.algo.discovery.powl.inductive.variants.dynamic_clustering import factory as dynamic_factory
from pm4py.algo.discovery.split_miner.concurrency import lifecycle
from pm4py.algo.discovery.split_miner.dtypes.complex_log import parse_complex_log
from pm4py.algo.discovery.split_miner.dtypes.working_graph import WorkingGraph
from pm4py.algo.discovery.split_miner.or_min import or_split
from pm4py.algo.querying.llm.utils import sql_utils
from pm4py.algo.simulation.playout.dfg.variants import performance
from pm4py.objects.log.obj import Event, EventLog, Trace
from pm4py.streaming.algo.conformance.temporal.variants import classic as streaming_temporal


class _Clusterer:
    def fit_predict(self, data):
        return [index % 2 for index in range(len(data))]


class MiscSubsystemsCoverageTest(unittest.TestCase):
    def test_dynamic_clustering_cut_order_projection_and_factory(self):
        cases = (
            ([['A']], set()),
            ([['A'], ['B']], {('A', 'B')}),
            ([['A'], ['B'], ['C']], {('A', 'B'), ('B', 'C')}),
            ([['A'], ['B'], ['C']], {('A', 'B'), ('B', 'A'), ('B', 'C')}),
            ([['A'], ['B'], ['C']], {('A', 'C')}),
        )
        self.assertIsNone(dynamic_cut.generate_order(*cases[0]))
        for clusters, eventually_follows in cases[1:-1]:
            order = dynamic_cut.generate_order(clusters, eventually_follows)
            self.assertIsNotNone(order)
            self.assertTrue(order.is_irreflexive())
        self.assertIsNone(dynamic_cut.generate_order(*cases[-1]))

        data = IMDataStructureUVCL(Counter({('A', 'B', 'C'): 3, ('A', 'C'): 1}))
        held = dynamic_cut.DynamicClusteringPartialOrderCutUVCL.holds(data)
        self.assertIsNotNone(held)
        applied = dynamic_cut.DynamicClusteringPartialOrderCutUVCL.apply(data)
        self.assertIsNotNone(applied)
        self.assertEqual(len(applied[0].children), len(applied[1]))
        with self.assertRaises(Exception):
            dynamic_cut.DynamicClusteringPartialOrderCut.operator()
        self.assertEqual(3, len(dynamic_factory.CutFactoryPOWLDynamicClustering.get_cuts(data)))
        self.assertIsNotNone(dynamic_factory.CutFactoryPOWLDynamicClustering.find_cut(data))
        singleton = IMDataStructureUVCL(Counter({('A',): 1}))
        self.assertIsNone(dynamic_factory.CutFactoryPOWLDynamicClustering.find_cut(singleton))

    @staticmethod
    def _lifecycle_log():
        base = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
        trace1 = Trace(
            [
                Event({'concept:name': 'A', 'lifecycle:transition': 'start', 'time:timestamp': base}),
                Event({'concept:name': 'B', 'lifecycle:transition': 'start', 'time:timestamp': base + datetime.timedelta(seconds=1)}),
                Event({'concept:name': 'A', 'lifecycle:transition': 'complete', 'time:timestamp': base + datetime.timedelta(seconds=2)}),
                Event({'concept:name': 'B', 'lifecycle:transition': 'complete', 'time:timestamp': base + datetime.timedelta(seconds=3)}),
            ]
        )
        trace2 = Trace(
            [
                Event({'concept:name': 'A', 'lifecycle:transition': 'start', 'time:timestamp': base}),
                Event({'concept:name': 'A', 'lifecycle:transition': 'complete', 'time:timestamp': base + datetime.timedelta(seconds=1)}),
            ]
        )
        return EventLog([trace1, trace2])

    def test_split_miner_complex_lifecycle_concurrency_and_or_matching(self):
        result = parse_complex_log(
            self._lifecycle_log(), 'concept:name', 'lifecycle:transition'
        )
        self.assertTrue(result.is_complex)
        self.assertTrue(result.overlap)
        self.assertIn(frozenset(('A', 'B')), result.potential_ors)
        simple = parse_complex_log(
            EventLog([Trace([Event({'concept:name': 'A'})])]),
            'concept:name',
            'lifecycle:transition',
        )
        self.assertFalse(simple.is_complex)
        self.assertFalse(simple.overlap)

        dfg = {
            ('start', 'A'): 3,
            ('start', 'B'): 3,
            ('A', 'B'): 2,
            ('B', 'A'): 2,
            ('A', 'end'): 3,
            ('B', 'end'): 3,
        }
        concurrent = lifecycle.apply_overlap_concurrency(
            dfg,
            {frozenset(('A', 'B')): 5},
            {'A': 5, 'B': 5},
            0.1,
        )
        self.assertTrue(concurrent.concurrent_pairs)
        guarded = lifecycle.apply_overlap_concurrency(
            {('A', 'B'): 1, ('B', 'A'): 1},
            {frozenset(('A', 'B')): 2},
            {'A': 2, 'B': 2},
            0.1,
        )
        self.assertFalse(guarded.concurrent_pairs)

        graph = WorkingGraph()
        for kind, node_id in (
            ('start', 's'), ('and', 'split'), ('task', 'a'), ('task', 'b'),
            ('task', 'c'), ('and', 'join'), ('end', 'e')
        ):
            graph.add_node(kind, label=node_id.upper(), node_id=node_id)
        graph.start_id, graph.end_id = 's', 'e'
        for source, target in (
            ('s', 'split'), ('split', 'a'), ('split', 'b'), ('split', 'c'),
            ('a', 'join'), ('b', 'join'), ('c', 'join'), ('join', 'e')
        ):
            graph.add_edge(source, target)
        pairs = {
            frozenset(('A', 'B')),
            frozenset(('A', 'C')),
            frozenset(('B', 'C')),
        }
        or_split.apply_or_split_heuristic(graph, pairs)
        self.assertEqual('or', graph.nodes['split'].kind)
        self.assertEqual('or', graph.nodes['join'].kind)
        or_split.apply_or_split_heuristic(graph, set())

    def test_streaming_temporal_profile_complete_incomplete_and_deviation(self):
        checker = streaming_temporal.apply(
            {('A', 'B'): (5.0, 1.0), ('B', 'C'): (1.0, 0.0)},
            parameters={streaming_temporal.Parameters.ZETA: 1.0},
        )
        base = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
        checker.receive(Event({'concept:name': 'missing'}))
        checker.receive(Event({
            'case:concept:name': '1', 'concept:name': 'A',
            'time:timestamp': base,
        }))
        checker.receive(Event({
            'case:concept:name': '1', 'concept:name': 'B',
            'time:timestamp': base + datetime.timedelta(seconds=20),
        }))
        checker.receive(Event({
            'case:concept:name': '1', 'concept:name': 'C',
            'time:timestamp': base + datetime.timedelta(seconds=30),
        }))
        result = checker.get()
        self.assertIn('1', result)
        self.assertEqual(2, len(result['1']))

    @unittest.skipUnless(
        importlib.util.find_spec("sklearn") and importlib.util.find_spec("polars"),
        "scikit-learn and polars are required",
    )
    def test_dfg_performance_playout_profiles_sql_and_polars_enrichment(self):
        from pm4py.objects.log.util import pl_lazy_extra_utils

        dfg = {('A', 'B'): 4, ('A', 'C'): 1, ('B', 'D'): 4, ('C', 'D'): 1}
        perf = {
            ('A', 'B'): {'mean': 2.0}, ('A', 'C'): 1.0,
            ('B', 'D'): 0, ('C', 'D'): 3.0,
        }
        with mock.patch.object(performance, 'choice', side_effect=lambda values, *_args, **_kwargs: [values[0]]), mock.patch.object(
            performance, 'exponential', side_effect=lambda value: value
        ):
            simulated = performance.apply(
                dfg,
                {'A': 5},
                {'D': 5},
                parameters={
                    performance.Parameters.NUM_TRACES: 3,
                    performance.Parameters.PERFORMANCE_DFG: perf,
                    performance.Parameters.CASE_ARRIVAL_RATE: 4,
                },
            )
        self.assertEqual(3, len(simulated))
        self.assertTrue(all(len(trace) == 3 for trace in simulated))
        self.assertIsNone(performance.dict_based_choice({'A': 0}))
        with self.assertRaises(Exception):
            performance.apply(dfg, {'A': 1}, {'D': 1}, parameters={'num_traces': 1})

        clustered = list(
            sklearn_profiles.apply(
                EventLog([
                    Trace([Event({'concept:name': 'A'}), Event({'concept:name': 'B'})]),
                    Trace([Event({'concept:name': 'A'}), Event({'concept:name': 'C'})]),
                    Trace([Event({'concept:name': 'D'})]),
                ]),
                parameters={sklearn_profiles.Parameters.SKLEARN_CLUSTERER: _Clusterer()},
            )
        )
        self.assertEqual(2, len(clustered))
        masked = sql_utils.mask_non_alphanumeric("select 'é' — ok")
        self.assertNotIn('—', masked)
        self.assertEqual("select 'é' — ok", sql_utils.restore_non_alphanumeric(masked))

        import polars as pl

        lazy = pl.DataFrame({
            'case:concept:name': ['1', '1', '2'],
            'time:timestamp': [
                datetime.datetime(2024, 1, 1),
                datetime.datetime(2024, 1, 2),
                datetime.datetime(2024, 2, 1),
            ],
            '@@count': [9, 9, 9],
            '@@case_throughput_right': [0, 0, 0],
        }).lazy()
        enriched = pl_lazy_extra_utils.compute_extra_columns(lazy).collect()
        self.assertIn('@@case_start_week', enriched.columns)
        self.assertEqual([1, 1, 1], enriched['@@count'].to_list())
        compact = pl_lazy_extra_utils.compute_extra_columns(
            lazy,
            parameters={pl_lazy_extra_utils.Parameters.COMPUTE_EXTRA_TEMPORAL_FEATURES: False},
        ).collect()
        self.assertNotIn('@@case_start_week', compact.columns)

    def test_top_level_connector_facades_and_ocel_conversions(self):
        from pm4py import connectors
        from pm4py.algo.connectors.variants import (
            camunda_workflow, chrome_history, firefox_history, github_repo,
            outlook_calendar, outlook_mail_extractor, sap_accounting, sap_o2c,
            windows_events,
        )

        dataframe = pd.DataFrame({
            'case:concept:name': ['1'],
            'concept:name': ['A'],
            'time:timestamp': [pd.Timestamp('2024-01-01', tz='UTC')],
            'org:resource': ['r'],
            'recipients': [['x']],
            'topic': ['t'],
            'case:subject': ['s'],
            'case:process_id': ['p'],
            'case:order_id': ['o'],
            'case:item': ['i'],
            'case:delivery': ['d'],
            'case:invoice': ['v'],
        })
        modules = (
            camunda_workflow, chrome_history, firefox_history, github_repo,
            outlook_calendar, outlook_mail_extractor, sap_accounting, sap_o2c,
            windows_events,
        )
        with ExitStack() as stack:
            for module in modules:
                stack.enter_context(mock.patch.object(module, 'apply', return_value=dataframe))
            self.assertIs(connectors.extract_log_outlook_mails(), dataframe)
            self.assertIs(connectors.extract_log_outlook_calendar('u', 3), dataframe)
            self.assertIs(connectors.extract_log_windows_events(), dataframe)
            self.assertIs(connectors.extract_log_chrome_history('chrome'), dataframe)
            self.assertIs(connectors.extract_log_firefox_history('firefox'), dataframe)
            self.assertIs(connectors.extract_log_github('o', 'r', 't'), dataframe)
            self.assertIs(connectors.extract_log_camunda_workflow('c'), dataframe)
            self.assertIs(connectors.extract_log_sap_o2c('c', 'p'), dataframe)
            self.assertIs(connectors.extract_log_sap_accounting('c', 'p'), dataframe)
            sentinel = object()
            with mock.patch.object(pm4py, 'convert_log_to_ocel', return_value=sentinel):
                self.assertIs(connectors.extract_ocel_outlook_mails(), sentinel)
                self.assertIs(connectors.extract_ocel_outlook_calendar('u', 3), sentinel)
                self.assertIs(connectors.extract_ocel_windows_events(), sentinel)
                self.assertIs(connectors.extract_ocel_chrome_history('chrome'), sentinel)
                self.assertIs(connectors.extract_ocel_firefox_history('firefox'), sentinel)
                self.assertIs(connectors.extract_ocel_github('o', 'r', 't'), sentinel)
                self.assertIs(connectors.extract_ocel_camunda_workflow('c'), sentinel)
                self.assertIs(connectors.extract_ocel_sap_o2c('c', 'p'), sentinel)
                self.assertIs(connectors.extract_ocel_sap_accounting('c', 'p'), sentinel)

    def test_cli_helpers_directory_product_and_failure_paths(self):
        from pm4py import cli

        read_log = getattr(cli, '__read_log')
        apply_sna = getattr(cli, '__apply_sna')
        get_output_name = getattr(cli, '__get_output_name')
        self.assertTrue(read_log(os.path.join(os.path.dirname(__file__), 'input_data', 'running-example.xes')) is not None)
        self.assertTrue(read_log(os.path.join(os.path.dirname(__file__), 'input_data', 'running-example.csv')) is not None)
        for method in ('handover', 'working_together', 'similar_activities', 'subcontracting'):
            function_name = {
                'handover': 'discover_handover_of_work_network',
                'working_together': 'discover_working_together_network',
                'similar_activities': 'discover_activity_based_resource_similarity',
                'subcontracting': 'discover_subcontracting_network',
            }[method]
            with mock.patch.object(pm4py, function_name, return_value=method):
                self.assertEqual(method, apply_sna(object(), method))
        self.assertIsNone(apply_sna(object(), 'unknown'))
        self.assertEqual('a_b_Dummy.txt', get_output_name(['/x/a.xes', '/y/b.pnml'], 0, 'Dummy', '.txt'))

        calls = []
        with tempfile.TemporaryDirectory() as directory:
            input_dir = os.path.join(directory, 'inputs')
            output_dir = os.path.join(directory, 'outputs')
            os.mkdir(input_dir)
            for name in ('one.txt', 'two.txt', 'ignored.csv'):
                open(os.path.join(input_dir, name), 'w').close()
            cli.methods['CoverageDummy'] = {
                'inputs': ['.txt'],
                'output_extension': '.out',
                'method': lambda args: calls.append(args),
            }
            try:
                with mock.patch.object(sys, 'argv', ['pm4py', 'CoverageDummy', input_dir, output_dir]):
                    cli.cli_interface()
            finally:
                del cli.methods['CoverageDummy']
        self.assertEqual(2, len(calls))
        with mock.patch.object(sys, 'argv', ['pm4py', 'missing']):
            with self.assertRaises(Exception):
                cli.cli_interface()

    def test_windows_click_logger_with_fake_platform_modules(self):
        class Listener:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                self.started = self.stopped = self.joined = False
            def start(self): self.started = True
            def stop(self): self.stopped = True
            def join(self): self.joined = True

        key = types.SimpleNamespace(**{
            name: name for name in (
                'tab', 'enter', 'esc', *[f'f{i}' for i in range(1, 21)], 'home', 'end'
            )
        })
        keyboard = types.ModuleType('pynput.keyboard')
        keyboard.Listener = Listener
        keyboard.Key = key
        mouse = types.ModuleType('pynput.mouse')
        mouse.Listener = Listener
        pynput = types.ModuleType('pynput')
        pynput.keyboard, pynput.mouse = keyboard, mouse
        window = types.SimpleNamespace(title='Title', _hWnd=10)
        gw = types.ModuleType('pygetwindow')
        gw.getActiveWindow = lambda: window
        win32process = types.ModuleType('win32process')
        win32process.GetWindowThreadProcessId = lambda hwnd: (1, os.getpid())
        psutil = types.ModuleType('psutil')
        psutil.NoSuchProcess = type('NoSuchProcess', (Exception,), {})
        psutil.Process = lambda pid: types.SimpleNamespace(name=lambda: 'python')
        for module in (pynput, keyboard, mouse, gw, win32process, psutil):
            module.__spec__ = importlib.machinery.ModuleSpec(module.__name__, loader=None)

        with mock.patch.dict(sys.modules, {
            'pynput': pynput,
            'pynput.keyboard': keyboard,
            'pynput.mouse': mouse,
            'pygetwindow': gw,
            'win32process': win32process,
            'psutil': psutil,
        }):
            sys.modules.pop('pm4py.streaming.connectors.windows.click_key_logger', None)
            module = importlib.import_module('pm4py.streaming.connectors.windows.click_key_logger')
            events = []
            logger = module.WindowsEventLogger(events, context_keys={key.enter})
            logger.record('Title', process_name='python', x=1, y=2, button='left')
            with mock.patch.object(module.time, 'sleep'):
                logger.on_click(3, 4, 'right', True)
            logger.on_click(3, 4, 'right', False)
            logger.on_key_release(key.enter)
            logger.on_key_release('ignored')
            logger.run()
            logger.stop()
            self.assertEqual(3, len(events))
            self.assertTrue(logger.mouse_listener.started)
            self.assertIsInstance(logger.get_process_name(10), str)


if __name__ == '__main__':
    unittest.main()

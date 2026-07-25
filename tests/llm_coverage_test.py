import contextlib
import os
import sys
import tempfile
import types
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import pandas as pd

import pm4py
from pm4py import llm
from pm4py.algo.querying.llm.connectors import anthropic, google, openai


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class LlmCoverageTest(unittest.TestCase):
    @staticmethod
    @contextlib.contextmanager
    def _mock_requests_post(return_value):
        """Provide the lazily imported requests module without requiring it."""
        requests_module = types.ModuleType("requests")
        requests_module.post = mock.Mock(return_value=return_value)
        with mock.patch.dict(sys.modules, {"requests": requests_module}):
            yield requests_module.post

    @staticmethod
    def _input_path(*parts):
        return os.path.join(os.path.dirname(__file__), "input_data", *parts)

    @staticmethod
    def _dataframe():
        base = datetime(2024, 1, 1, tzinfo=timezone.utc)
        return pd.DataFrame(
            [
                {"case:concept:name": "1", "concept:name": "A", "time:timestamp": base, "resource": "r1", "cost": 1.0},
                {"case:concept:name": "1", "concept:name": "B", "time:timestamp": base + timedelta(minutes=2), "resource": "r2", "cost": 2.0},
                {"case:concept:name": "2", "concept:name": "A", "time:timestamp": base + timedelta(hours=1), "resource": "r1", "cost": 3.0},
                {"case:concept:name": "2", "concept:name": "C", "time:timestamp": base + timedelta(hours=1, minutes=4), "resource": "r3", "cost": 4.0},
            ]
        )

    def test_openai_connector_chat_responses_images_and_errors(self):
        with tempfile.NamedTemporaryFile(suffix=".png") as image:
            image.write(b"image-bytes")
            image.flush()
            self.assertTrue(openai.encode_image(image.name))

            chat = _Response({"choices": [{"message": {"content": "chat answer"}}]})
            with self._mock_requests_post(chat) as request:
                answer = openai.apply(
                    "prompt",
                    parameters={
                        "api_url": "https://proxy.example/v1",
                        "api_key": "key",
                        "openai_model": "model",
                        "image_path": image.name,
                        "max_tokens": 10,
                        "extra_payload": {"temperature": 0},
                        "use_responses_api": False,
                    },
                )
            self.assertEqual("chat answer", answer)
            self.assertTrue(request.call_args.args[0].endswith("/chat/completions"))
            self.assertEqual(0, request.call_args.kwargs["json"]["temperature"])

            responses = _Response({"output": [{"content": [{"text": "response answer"}]}]})
            with self._mock_requests_post(responses) as request:
                answer = openai.apply(
                    "prompt",
                    parameters={"api_url": "https://api.openai.com/v1/", "use_responses_api": True},
                )
            self.assertEqual("response answer", answer)
            self.assertTrue(request.call_args.args[0].endswith("responses"))

            with self._mock_requests_post(_Response({"error": {"message": "bad"}})):
                with self.assertRaisesRegex(Exception, "bad"):
                    openai.apply("prompt", parameters={"use_responses_api": True})

    def test_google_and_anthropic_connectors_with_images_and_errors(self):
        with tempfile.NamedTemporaryFile(suffix=".jpeg") as image:
            image.write(b"image-bytes")
            image.flush()
            self.assertTrue(google.encode_image(image.name))
            self.assertTrue(anthropic.encode_image(image.name))

            with self._mock_requests_post(
                _Response(
                    {"candidates": [{"content": {"parts": [{"text": "google answer"}]}}]}
                ),
            ) as request:
                answer = google.apply(
                    "prompt",
                    parameters={
                        "api_key": "key",
                        "google_model": "model",
                        "image_path": image.name,
                        "extra_payload": {"generationConfig": {}},
                    },
                )
            self.assertEqual("google answer", answer)
            self.assertIn("model:generateContent", request.call_args.args[0])

            with self._mock_requests_post(
                _Response({"error": {"message": "google bad"}})
            ):
                with self.assertRaisesRegex(Exception, "google bad"):
                    google.apply("prompt", parameters={"api_key": "key"})

            with self._mock_requests_post(
                _Response({"content": [{"text": "anthropic answer"}]}),
            ) as request:
                answer = anthropic.apply(
                    "prompt",
                    parameters={
                        "api_url": "https://proxy.example/v1",
                        "api_key": "key",
                        "anthropic_model": "model",
                        "image_path": image.name,
                        "thinking_tokens": 70000,
                        "max_tokens": 70000,
                        "extra_payload": {"temperature": 0},
                    },
                )
            self.assertEqual("anthropic answer", answer)
            self.assertEqual(128000, request.call_args.kwargs["json"]["max_tokens"])
            self.assertIn("anthropic-beta", request.call_args.kwargs["headers"])

            with self._mock_requests_post(
                _Response({"error": {"message": "anthropic bad"}})
            ):
                with self.assertRaisesRegex(Exception, "anthropic bad"):
                    anthropic.apply("prompt")

    def test_public_query_wrappers_forward_parameters(self):
        with mock.patch.object(openai, "apply", return_value="openai") as call:
            self.assertEqual(
                "openai",
                llm.openai_query(
                    "p",
                    api_key="key",
                    openai_model="model",
                    api_url="https://example",
                    extra_payload={"x": 1},
                    max_tokens=5,
                ),
            )
            self.assertEqual("key", call.call_args.kwargs["parameters"]["api_key"])
        with mock.patch.object(google, "apply", return_value="google"):
            self.assertEqual("google", llm.google_query("p", api_key="key", model="model", extra_payload={"x": 1}))
        with mock.patch.object(anthropic, "apply", return_value="anthropic"):
            self.assertEqual("anthropic", llm.anthropic_query("p", api_key="key", model="model", extra_payload={"x": 1}))

    def test_textual_abstraction_public_api(self):
        dataframe = self._dataframe()
        abstractions = [
            llm.abstract_dfg(dataframe, max_len=4000),
            llm.abstract_variants(dataframe, max_len=4000),
            llm.abstract_event_stream(dataframe, max_len=4000),
            llm.abstract_log_attributes(dataframe, max_len=4000),
            llm.abstract_log_features(dataframe, max_len=4000),
        ]
        self.assertTrue(all(isinstance(value, str) and value for value in abstractions))

        legacy_log = pm4py.convert_to_event_log(dataframe)
        self.assertIn("A", llm.abstract_case(legacy_log[0]))
        net, initial_marking, final_marking = pm4py.read_pnml(
            self._input_path("running-example.pnml")
        )
        self.assertIn("Petri", llm.abstract_petri_net(net, initial_marking, final_marking))
        self.assertTrue(llm.abstract_temporal_profile({("A", "B"): (2.0, 0.5)}))

        declare_model = pm4py.discover_declare(legacy_log)
        skeleton = pm4py.discover_log_skeleton(legacy_log)
        self.assertTrue(llm.abstract_declare(declare_model))
        self.assertTrue(llm.abstract_log_skeleton(skeleton))

        ocel = pm4py.read_ocel(self._input_path("ocel", "example_log.jsonocel"))
        self.assertTrue(llm.abstract_ocel(ocel))
        self.assertTrue(llm.abstract_ocel_ocdfg(ocel, max_len=4000))
        self.assertTrue(llm.abstract_ocel_features(ocel, "element", max_len=4000))

    def test_clustering_safe_sql_prompts_hypotheses_and_visual_explanation(self):
        dataframe = self._dataframe()
        executor = mock.Mock(
            return_value='```json[{"name": "starts A", "regex": "^A"}]```'
        )
        clusters = llm.clustering(dataframe, executor=executor)
        self.assertEqual(1, len(clusters))
        self.assertEqual("starts A", clusters[0][0])
        self.assertEqual(4, len(clusters[0][1]))

        validate = llm.__dict__["__validate_safe_select_query"]
        self.assertEqual("SELECT * FROM dataframe", validate("SELECT * FROM dataframe;"))
        self.assertEqual("WITH x AS (SELECT 1) SELECT * FROM x", validate("WITH x AS (SELECT 1) SELECT * FROM x"))
        for unsafe in ("", "SELECT 1; DROP TABLE x", "SELECT 1 -- comment", "DELETE FROM x", "SELECT * FROM read_csv('x')"):
            with self.assertRaises(ValueError):
                validate(unsafe)

        sql_executor = mock.Mock(return_value="```sql\nSELECT * FROM dataframe\n```")
        self.assertEqual(
            "SELECT * FROM dataframe",
            llm.nlp_to_log_query(dataframe, "all rows", executor=sql_executor, execute_query=False),
        )
        self.assertEqual(
            "SELECT * FROM dataframe",
            llm.nlp_to_log_filter(dataframe, "activity A", executor=sql_executor, execute_query=False),
        )
        self.assertIn("database query", llm.nlp_to_log_query(dataframe, "all rows", obtain_query=False))
        self.assertIn("filter all the events", llm.nlp_to_log_filter(dataframe, "activity A", obtain_query=False))

        duckdb_module = types.ModuleType("duckdb")
        with mock.patch.dict(sys.modules, {"duckdb": duckdb_module}):
            hypothesis_prompt = llm.automated_hypotheses_formulation(
                dataframe, obtain_query=False, max_len=3000
            )
        self.assertIn("hypotheses", hypothesis_prompt)

        def saver(value, path, **kwargs):
            with open(path, "wb") as file:
                file.write(b"png")
            return f"visualization of {value}"

        visual_connector = mock.Mock(return_value="explanation")
        self.assertEqual(
            "explanation",
            llm.explain_visualization(
                saver, "model", connector=visual_connector, custom="value"
            ),
        )
        self.assertIn("visualization of model", visual_connector.call_args.args[0])
        self.assertIn("image_path", visual_connector.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()

from collections import Counter
import unittest
from pm4py.objects.oc_causal_net.creation.factory import create_oc_causal_net
from pm4py.objects.oc_causal_net.semantics import OCCausalNetSemantics, OCCausalNetState


class OCCausalNetSemanticsTest(unittest.TestCase):

    def test_enabled_bindings(self):
        occn = occn_multi_ot_multi_arc()

        state = OCCausalNetState()
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(enabled_bindings, ())

        state = OCCausalNetState({"a": Counter([("START_order", "o1", "order")])})
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(len(enabled_bindings), 0)

        state = OCCausalNetState(
            {
                "a": Counter(
                    [("START_order", "o1", "order"), ("START_item", "i1", "item")]
                )
            }
        )
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(len(enabled_bindings), 1)

        state = OCCausalNetState(
            {
                "a": Counter(
                    [
                        ("START_order", "o1", "order"),
                        ("START_item", "i1", "item"),
                        ("START_item", "i2", "item"),
                    ]
                )
            }
        )
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(len(enabled_bindings), 3)

    def test_enabled_bindings_2(self):
        occn = occn_multi_ot_multi_min_0()

        state = OCCausalNetState()
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(enabled_bindings, ())

        state = OCCausalNetState({"a": Counter([("START_order", "o1", "order")])})
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(len(enabled_bindings), 1)

        state = OCCausalNetState(
            {
                "a": Counter(
                    [("START_order", "o1", "order"), ("START_item", "i1", "item")]
                )
            }
        )
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(len(enabled_bindings), 2)

        state = OCCausalNetState(
            {
                "a": Counter(
                    [
                        ("START_order", "o1", "order"),
                        ("START_item", "i1", "item"),
                        ("START_item", "i2", "item"),
                    ]
                )
            }
        )
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(len(enabled_bindings), 4)

    def test_enabled_bindings_3(self):

        act_to_idx = {
            "START_order": 0,
            "START_item": 1,
            "a": 2,
            "b": 3,
            "END_order": 4,
            "END_item": 5,
        }

        ot_to_idx = {"order": 0, "item": 1}

        occn = occn_multi_ot_multi_min_0()

        state = OCCausalNetState()
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(enabled_bindings, ())

        state = OCCausalNetState({2: Counter([(0, "o1", 0)])})
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(
            occn, "a", state, act_to_idx, ot_to_idx
        )
        self.assertEqual(len(enabled_bindings), 1)

        state = OCCausalNetState({2: Counter([(0, "o1", 0), (1, "i1", 1)])})
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(
            occn, "a", state, act_to_idx, ot_to_idx
        )
        self.assertEqual(len(enabled_bindings), 2)

        state = OCCausalNetState(
            {2: Counter([(0, "o1", 0), (1, "i1", 1), (1, "i2", 1)])}
        )
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(
            occn, "a", state, act_to_idx, ot_to_idx
        )
        self.assertEqual(len(enabled_bindings), 4)

    def test_enabled_bindings_4(self):
        occn = occn_multi_ot_multi_marker()

        state = OCCausalNetState()
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(enabled_bindings, ())

        state = OCCausalNetState({"a": Counter([("START_order", "o1", "order")])})
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(enabled_bindings, ())

        state = OCCausalNetState(
            {
                "a": Counter(
                    [("START_order", "o1", "order"), ("START_item", "i1", "item")]
                )
            }
        )
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(len(enabled_bindings), 2)

        state = OCCausalNetState({"a": Counter([("START_item", "i1", "item")])})
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(len(enabled_bindings), 1)

        state = OCCausalNetState(
            {
                "a": Counter(
                    [
                        ("START_order", "o1", "order"),
                        ("START_item", "i1", "item"),
                        ("START_item", "i1", "item"),
                    ]
                )
            }
        )
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(len(enabled_bindings), 2)

        state = OCCausalNetState(
            {
                "a": Counter(
                    [
                        ("START_order", "o1", "order"),
                        ("START_item", "i1", "item"),
                        ("START_item", "i2", "item"),
                    ]
                )
            }
        )
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(len(enabled_bindings), 6)

    def test_enabled_bindings_5(self):
        occn = occn_multi_ot_multi_marker_redundant_mg()

        state = OCCausalNetState()
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(enabled_bindings, ())

        state = OCCausalNetState({"a": Counter([("START_order", "o1", "order")])})
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(enabled_bindings, ())

        state = OCCausalNetState(
            {
                "a": Counter(
                    [("START_order", "o1", "order"), ("START_item", "i1", "item")]
                )
            }
        )
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(len(enabled_bindings), 2)

        state = OCCausalNetState({"a": Counter([("START_item", "i1", "item")])})
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(len(enabled_bindings), 1)

        state = OCCausalNetState(
            {
                "a": Counter(
                    [
                        ("START_order", "o1", "order"),
                        ("START_item", "i1", "item"),
                        ("START_item", "i1", "item"),
                    ]
                )
            }
        )
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(len(enabled_bindings), 2)

        state = OCCausalNetState(
            {
                "a": Counter(
                    [
                        ("START_order", "o1", "order"),
                        ("START_item", "i1", "item"),
                        ("START_item", "i2", "item"),
                    ]
                )
            }
        )
        enabled_bindings = OCCausalNetSemantics.enabled_bindings(occn, "a", state)
        self.assertEqual(len(enabled_bindings), 6)

    def test_enabled_start_bindings(self):
        occn = occn_start_parallel()

        enabled_bindings = OCCausalNetSemantics.enabled_bindings_start_activity(
            occn, "START_order", "order", set()
        )
        self.assertEqual(len(enabled_bindings), 0)

        enabled_bindings = OCCausalNetSemantics.enabled_bindings_start_activity(
            occn, "START_order", "order", {"o1"}
        )
        self.assertEqual(len(enabled_bindings), 3)

        enabled_bindings = OCCausalNetSemantics.enabled_bindings_start_activity(
            occn, "START_order", "order", {"o1", "o2"}
        )
        self.assertEqual(len(enabled_bindings), 10)
        for binding in enabled_bindings:
            prod_tuple = binding[2]
            prod_dict = {
                succ:
                    {
                        ot: set(objects)
                        for ot, objects in obj_per_ot
                    }
                for succ, obj_per_ot in prod_tuple
            }
            self.assertIsNotNone(OCCausalNetSemantics.is_binding_enabled(occn, "START_order", None, prod_dict, OCCausalNetState()))

    def test_state_repr_non_empty(self):
        state = OCCausalNetState({"a": Counter([("START_order", "o1", "order")])})
        rep = repr(state)
        self.assertIn("START_order", rep)
        self.assertIn("o1[order]", rep)
        self.assertIn("a", rep)

    def test_enabled_bindings_respects_key_constraints(self):
        occn = occn_key_constraint_no_overlap()

        # Same object for both predecessor activities violates key constraints.
        violating_state = OCCausalNetState(
            {"a": Counter([("x", "o1", "order"), ("y", "o1", "order")])}
        )
        self.assertEqual(
            OCCausalNetSemantics.enabled_bindings(occn, "a", violating_state), ()
        )

        valid_state = OCCausalNetState(
            {"a": Counter([("x", "o1", "order"), ("y", "o2", "order")])}
        )
        self.assertEqual(
            len(OCCausalNetSemantics.enabled_bindings(occn, "a", valid_state)), 1
        )


def occn_multi_ot_multi_arc():
    marker_groups = {
        "START_order": {
            "omg": [
                [("a", "order", (1, 1), 0)],
            ],
        },
        "START_item": {
            "omg": [
                [("a", "item", (1, -1), 0)],
            ],
        },
        "a": {
            "img": [
                [
                    ("START_order", "order", (1, 1), 0),
                    ("START_item", "item", (1, -1), 0),
                ],
            ],
            "omg": [
                [
                    ("b", "order", (1, 1), 0),
                    ("b", "item", (1, -1), 0),
                ],
            ],
        },
        "b": {
            "img": [
                [
                    ("a", "order", (1, 1), 0),
                    ("a", "item", (1, -1), 0),
                ],
            ],
            "omg": [
                [
                    ("END_order", "order", (1, 1), 0),
                    ("END_item", "item", (1, -1), 0),
                ],
            ],
        },
        "END_order": {
            "img": [
                [("b", "order", (1, 1), 0)],
            ]
        },
        "END_item": {
            "img": [
                [("b", "item", (1, -1), 0)],
            ]
        },
    }

    occn = create_oc_causal_net(marker_groups)
    return occn


def occn_key_constraint_no_overlap():
    marker_groups = {
        "x": {"omg": [[("a", "order", (1, 1), 1)]]},
        "y": {"omg": [[("a", "order", (1, 1), 2)]]},
        "a": {
            "img": [[("x", "order", (1, 1), 7), ("y", "order", (1, 1), 7)]],
            "omg": [[("END_order", "order", (2, 2), 0)]],
        },
        "END_order": {"img": [[("a", "order", (1, 1), 0)]]},
    }
    return create_oc_causal_net(marker_groups)


def occn_multi_ot_multi_min_0():
    marker_groups = {
        "START_order": {
            "omg": [
                [("a", "order", (1, 1), 0)],
            ],
        },
        "START_item": {
            "omg": [
                [("a", "item", (1, -1), 0)],
            ],
        },
        "a": {
            "img": [
                [
                    ("START_order", "order", (1, 1), 0),
                    ("START_item", "item", (0, -1), 0),
                ],
            ],
            "omg": [
                [
                    ("b", "order", (1, 1), 0),
                    ("b", "item", (0, -1), 0),
                ],
            ],
        },
        "b": {
            "img": [
                [
                    ("a", "order", (1, 1), 0),
                    ("a", "item", (0, -1), 0),
                ],
            ],
            "omg": [
                [
                    ("END_order", "order", (1, 1), 0),
                    ("END_item", "item", (0, -1), 0),
                ],
            ],
        },
        "END_order": {
            "img": [
                [("b", "order", (1, 1), 0)],
            ]
        },
        "END_item": {
            "img": [
                [("b", "item", (1, -1), 0)],
            ]
        },
    }

    occn = create_oc_causal_net(marker_groups)
    return occn


def occn_multi_ot_multi_marker():
    marker_groups = {
        "START_order": {
            "img": [],
            "omg": [
                [("a", "order", (1, 1), 0)],
            ],
        },
        "START_item": {
            "img": [],
            "omg": [
                [("a", "item", (1, -1), 0)],
            ],
        },
        "a": {
            "img": [
                [
                    ("START_order", "order", (1, 1), 0),
                    ("START_item", "item", (1, -1), 0),
                ],
                [
                    ("START_item", "item", (1, -1), 0),
                ],
            ],
            "omg": [
                [
                    ("END_order", "order", (1, 1), 0),
                    ("END_item", "item", (1, -1), 0),
                ],
                [
                    ("END_item", "item", (1, -1), 0),
                ],
            ],
        },
        "END_order": {
            "img": [
                [("a", "order", (1, 1), 0)],
            ]
        },
        "END_item": {
            "img": [
                [("a", "item", (1, -1), 0)],
            ]
        },
    }

    occn = create_oc_causal_net(marker_groups)
    return occn


def occn_multi_ot_multi_marker_redundant_mg():
    marker_groups = {
        "START_order": {
            "img": [],
            "omg": [
                [("a", "order", (1, 1), 0)],
            ],
        },
        "START_item": {
            "img": [],
            "omg": [
                [("a", "item", (1, -1), 0)],
            ],
        },
        "a": {
            "img": [
                [
                    ("START_order", "order", (1, 1), 0),
                    ("START_item", "item", (1, -1), 0),
                ],
                [
                    ("START_order", "order", (1, 1), 0),
                    ("START_item", "item", (1, 1), 0),
                ],
                [
                    ("START_order", "order", (1, 1), 0),
                    ("START_item", "item", (2, 2), 0),
                ],
                [
                    ("START_item", "item", (0, -1), 0),
                ],
                [
                    ("START_item", "item", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("END_order", "order", (1, 1), 0),
                    ("END_item", "item", (1, -1), 0),
                ],
                [
                    ("END_order", "order", (1, 1), 0),
                    ("END_item", "item", (1, 1), 0),
                ],
                [
                    ("END_item", "item", (0, -1), 0),
                ],
                [
                    ("END_item", "item", (1, -1), 0),
                ],
                [
                    ("END_item", "item", (1, -1), 0),
                ],
            ],
        },
        "END_order": {
            "img": [
                [("a", "order", (1, 1), 0)],
            ]
        },
        "END_item": {
            "img": [
                [("a", "item", (1, -1), 0)],
            ]
        },
    }

    occn = create_oc_causal_net(marker_groups)
    return occn


def occn_start_parallel():
    marker_groups = {
        "START_order": {
            "img": [],
            "omg": [
                [("a", "order", (1, 1), 0), ("b", "order", (1, 1), 0)],
                [("a", "order", (1, -1), 0)],
                [("b", "order", (1, -1), 0)],
            ],
        },
        "a": {
            "img": [
                [
                    ("START_order", "order", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("END_order", "order", (1, 1), 0),
                ],
            ],
        },
        "b": {
            "img": [
                [
                    ("START_order", "order", (1, 1), 0),
                ],
            ],
            "omg": [
                [
                    ("END_order", "order", (1, 1), 0),
                ],
            ],
        },
        "END_order": {
            "img": [
                [("a", "order", (1, 1), 0), ("b", "order", (1, 1), 0)],
                [("a", "order", (1, -1), 0)],
                [("b", "order", (1, -1), 0)],
            ]
        },
    }

    occn = create_oc_causal_net(marker_groups)
    return occn


if __name__ == "__main__":
    unittest.main()

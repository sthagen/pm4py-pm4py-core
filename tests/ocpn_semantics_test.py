from collections import Counter
import copy
import unittest
from pm4py.objects.ocpn.obj import OCPetriNet, OCMarking
from pm4py.objects.ocpn.semantics import OCPetriNetSemantics


class OCPN_Semantics_Test(unittest.TestCase):

    def test_enabled(self):

        def assert_enabled_transitions(ocpn, marking, enabled_transitions):
            self.assertEqual(enabled_transitions, OCPetriNetSemantics.enabled_transitions(ocpn, marking))

        ocpn = ocpn_big()
        places = {p.name: p for p in ocpn.places}
        transitions = {t.name: t for t in ocpn.transitions}

        marking1 = OCMarking(
            {places["o1"]: Counter(["order1"]), places["i1"]: Counter(["item1", "item2"])}
        )
        enabled1 = {transitions["po"]}
        assert_enabled_transitions(ocpn, marking1, enabled1)

        marking2 = OCMarking({places["o1"]: Counter(["order1"])})
        enabled2 = {transitions["po"]}
        assert_enabled_transitions(ocpn, marking2, enabled2)

        marking3 = OCMarking({places["i1"]: Counter(["item1"])})
        enabled3 = set()
        assert_enabled_transitions(ocpn, marking3, enabled3)

        marking4 = OCMarking(
            {places["o3"]: Counter(["order1"]), places["i3"]: Counter(["item1", "item2"])}
        )
        enabled4 = {transitions["sr"], transitions["pa"], transitions["sh"]}
        assert_enabled_transitions(ocpn, marking4, enabled4)

        marking5 = OCMarking()
        enabled5 = set()
        assert_enabled_transitions(ocpn, marking5, enabled5)

        marking6 = OCMarking(
            {
                places["o1"]: Counter(["order1"]),
                places["o2"]: Counter(["order1"]),
                places["o3"]: Counter(["order1"]),
                places["o4"]: Counter(["order1"]),
                places["i1"]: Counter(["item1"]),
                places["i2"]: Counter(["item1"]),
                places["i3"]: Counter(["item1"]),
                places["i4"]: Counter(["item1"]),
            }
        )
        enabled6 = set(transitions.values())
        assert_enabled_transitions(ocpn, marking6, enabled6)
        
    def test_fire(self):
        ocpn = ocpn_big()
        places = {p.name: p for p in ocpn.places}
        transitions = {t.name: t for t in ocpn.transitions}

        marking = OCMarking(
            {places["o1"]: Counter(["order1"]), places["i1"]: Counter(["item1", "item2"])}
        )
        objects = {"order": {"order1"}, "item": {"item1", "item2"}}
        new_marking = OCPetriNetSemantics.fire(ocpn, transitions["po"], marking, objects)
        self.assertEqual(new_marking[places["o2"]], Counter(["order1"]))
        self.assertEqual(new_marking[places["i2"]], Counter(["item1", "item2"]))

        marking = OCMarking(
            {places["o1"]: Counter({"order1": 2}), places["i1"]: Counter(["item1", "item2"])}
        )
        objects = {"order": {"order1"}, "item": {"item1", "item2"}}
        new_marking = OCPetriNetSemantics.fire(ocpn, transitions["po"], marking, objects)
        self.assertEqual(new_marking[places["o1"]], Counter(["order1"]))
        self.assertEqual(new_marking[places["o2"]], Counter(["order1"]))
        self.assertEqual(new_marking[places["i2"]], Counter(["item1", "item2"]))
        
        marking = OCMarking(
            {places["o1"]: Counter({"order1": 2}), places["i1"]: Counter(["item1", "item2"])}
        )
        objects = {"order": {"order1"}, "item": {"item1"}}
        new_marking = OCPetriNetSemantics.fire(ocpn, transitions["po"], marking, objects)
        self.assertEqual(new_marking[places["o1"]], Counter(["order1"]))
        self.assertEqual(new_marking[places["o2"]], Counter(["order1"]))
        self.assertEqual(new_marking[places["i1"]], Counter(["item2"]))
        self.assertEqual(new_marking[places["i2"]], Counter(["item1"]))

        marking = OCMarking(
            {places["o1"]: Counter({"order1": 2}), places["i1"]: Counter(["item1", "item2"]), places["i2"]: Counter(["item1"])}
        )
        objects = {"order": {"order1"}, "item": {"item1"}}
        new_marking = OCPetriNetSemantics.fire(ocpn, transitions["po"], marking, objects)
        self.assertEqual(new_marking[places["o1"]], Counter(["order1"]))
        self.assertEqual(new_marking[places["o2"]], Counter(["order1"]))
        self.assertEqual(new_marking[places["i1"]], Counter(["item2"]))
        self.assertEqual(new_marking[places["i2"]], Counter({"item1": 2}))
        
        marking = OCMarking(
            {places["o1"]: Counter(["order1"])}
        )
        objects = {"order": {"order1"}}
        new_marking = OCPetriNetSemantics.fire(ocpn, transitions["po"], marking, objects)
        self.assertEqual(new_marking[places["o1"]], Counter())
        self.assertEqual(new_marking[places["o2"]], Counter(["order1"]))
        self.assertEqual(new_marking[places["i1"]], Counter())
        self.assertEqual(new_marking[places["i2"]], Counter())
        
    def test_fire_2(self):
        ocpn = ocpn_multi_start()
        places = {p.name: p for p in ocpn.places}
        transitions = {t.name: t for t in ocpn.transitions}
        
        marking = OCMarking(
            {places["o1"]: Counter(["order1"]), places["o3"]: Counter(["order1"])}
        )
        objects = {"order": {"order1"}}
        new_marking = OCPetriNetSemantics.fire(ocpn, transitions["a"], marking, objects)
        self.assertEqual(new_marking[places["o1"]], Counter())
        self.assertEqual(new_marking[places["o3"]], Counter())
        self.assertEqual(new_marking[places["o2"]], Counter(["order1"]))
        self.assertEqual(new_marking[places["o4"]], Counter(["order1"]))
        
        marking = OCMarking(
            {places["o1"]: Counter(["order1", "order2"]), places["o3"]: Counter(["order1"])}
        )
        objects = {"order": {"order1"}}
        new_marking = OCPetriNetSemantics.fire(ocpn, transitions["a"], marking, objects)
        self.assertEqual(new_marking[places["o1"]], Counter(["order2"]))
        self.assertEqual(new_marking[places["o3"]], Counter())
        self.assertEqual(new_marking[places["o2"]], Counter(["order1"]))
        self.assertEqual(new_marking[places["o4"]], Counter(["order1"]))


    def test_fire_3(self):
        ocpn = ocpn_muli_variable_2()
        places = {p.name: p for p in ocpn.places}
        transitions = {t.name: t for t in ocpn.transitions}
        
        
        marking = OCMarking(
            {places["p1"]: Counter(["order1", "order2"]), places["p4"]: Counter(["box1", "box2", "box3"])}
        )
        objects = {"order": {"order1", "order2"}, "box": {"box1", "box2"}}
        new_marking = OCPetriNetSemantics.fire(ocpn, transitions["a"], marking, objects)
        self.assertEqual(new_marking[places["p1"]], Counter())
        self.assertEqual(new_marking[places["p4"]], Counter(["box3"]))
        self.assertEqual(new_marking[places["p2"]], Counter(["order1", "order2"]))
        self.assertEqual(new_marking[places["p5"]], Counter(["box1", "box2"]))
        self.assertEqual(new_marking[places["p6"]], Counter(["box1", "box2"]))

    def test_fire_does_not_mutate_input_marking(self):
        ocpn = ocpn_big()
        places = {p.name: p for p in ocpn.places}
        transitions = {t.name: t for t in ocpn.transitions}
        marking = OCMarking(
            {places["o1"]: Counter(["order1"]), places["i1"]: Counter(["item1"])}
        )
        marking_before = OCMarking(
            {place: counter.copy() for place, counter in marking.items()}
        )

        OCPetriNetSemantics.fire(
            ocpn, transitions["po"], marking, {"order": {"order1"}, "item": {"item1"}}
        )

        self.assertEqual(marking, marking_before)

    def test_deepcopy_preserves_markings(self):
        ocpn = ocpn_big()
        copied = copy.deepcopy(ocpn)

        def to_name_counter(marking):
            return {place.name: counter for place, counter in marking.items()}

        self.assertIsNotNone(copied.initial_marking)
        self.assertIsNotNone(copied.final_marking)
        self.assertEqual(
            to_name_counter(copied.initial_marking),
            to_name_counter(ocpn.initial_marking),
        )
        self.assertEqual(
            to_name_counter(copied.final_marking),
            to_name_counter(ocpn.final_marking),
        )
        self.assertTrue(all(p in copied.places for p in copied.initial_marking.keys()))
        self.assertTrue(all(p in copied.places for p in copied.final_marking.keys()))
        
    def assert_bindings_equal(self, possible_bindings_iter, expected_bindings):
            # Check that all iterator elements are in the expected bindings
            for binding in possible_bindings_iter:
                self.assertIn(binding, expected_bindings)
                expected_bindings.remove(binding)
            # Assert none are left
            self.assertEqual(len(expected_bindings), 0)

    def test_possible_bindings(self):
        ocpn = ocpn_big()
        places = {p.name: p for p in ocpn.places}
        transitions = {t.name: t for t in ocpn.transitions}
        
        marking = OCMarking(
            {places["o1"]: Counter(["o1", "o2"]), places["i1"]: Counter(["i1", "i2"])}
        )
        
        possible_bindings_iter = OCPetriNetSemantics.get_possible_bindings(ocpn, transitions["po"], marking)
        expected_bindings = [
            {
                "order": {"o1"},
            },
            {
                "order": {"o2"},
            },
            {
                "order": {"o1"},
                "item": {"i1"}
            },
            {
                "order": {"o2"},
                "item": {"i1"}
            },
            {
                "order": {"o1"},
                "item": {"i2"}
            },
            {
                "order": {"o2"},
                "item": {"i2"}
            },
            {
                "order": {"o1"},
                "item": {"i1", "i2"}
            },
            {
                "order": {"o2"},
                "item": {"i1", "i2"}
            }]
        
        
        self.assert_bindings_equal(possible_bindings_iter, expected_bindings)
        
        
        marking = OCMarking(
            {places["i1"]: Counter(["i1", "i2"])}
        )
        possible_bindings_iter = OCPetriNetSemantics.get_possible_bindings(ocpn, transitions["po"], marking)
        expected_bindings = []
        self.assert_bindings_equal(possible_bindings_iter, expected_bindings)
        
        
        marking = OCMarking(
            {places["o1"]: Counter(["o1", "o2"])}
        )
        possible_bindings_iter = OCPetriNetSemantics.get_possible_bindings(ocpn, transitions["po"], marking)
        expected_bindings = [
            {
                "order": {"o1"},
            },
            {
                "order": {"o2"},
            },]
        self.assert_bindings_equal(possible_bindings_iter, expected_bindings)
        
        marking = OCMarking(
            {places["o1"]: Counter(["o1", "o2"])}
        )
        possible_bindings_iter = OCPetriNetSemantics.get_possible_bindings(ocpn, transitions["si"], marking)
        expected_bindings = []
        self.assert_bindings_equal(possible_bindings_iter, expected_bindings)
        
        
        marking = OCMarking(
            {places["o2"]: Counter(["o1"]), places["o3"]: Counter(["o1", "o2"])}
        )
        possible_bindings_iter = OCPetriNetSemantics.get_possible_bindings(ocpn, transitions["si"], marking)
        expected_bindings = [
            {
                "order": {"o1"},
            }]
        self.assert_bindings_equal(possible_bindings_iter, expected_bindings)
        
        
        
        
        
        
        
        
    def test_possible_bindings_2(self):
        ocpn = ocpn_muli_variable_2()
        places = {p.name: p for p in ocpn.places}
        transitions = {t.name: t for t in ocpn.transitions}
        
        marking = OCMarking(
            {places["p1"]: Counter(["o1"]), places["p4"]: Counter(["b1", "b2"])}
        )
        possible_bindings_iter = OCPetriNetSemantics.get_possible_bindings(ocpn, transitions["a"], marking)
        expected_bindings = [
            {
                "box": {"b1"},
            },
            {
                "box": {"b2"},
            },
            {
                "box": {"b1", "b2"},
            },
            {
                "order": {"o1"},
            },
            {
                "order": {"o1"},
                "box": {"b1"},
            },
            {
                "order": {"o1"},
                "box": {"b2"},
            },
            {
                "order": {"o1"},
                "box": {"b1", "b2"},
            },
            ]
        self.assert_bindings_equal(possible_bindings_iter, expected_bindings)
        
        
    def test_possible_bindings_3(self):
        ocpn = ocpn_multi_start()
        places = {p.name: p for p in ocpn.places}
        transitions = {t.name: t for t in ocpn.transitions}
        
        marking = OCMarking(
            {places["o1"]: Counter(["o1"])}
        )
        possible_bindings_iter = OCPetriNetSemantics.get_possible_bindings(ocpn, transitions["a"], marking)
        expected_bindings = [
        ]
        self.assert_bindings_equal(possible_bindings_iter, expected_bindings)
        
        
        marking = OCMarking(
            {places["o1"]: Counter(["o1"]), places["o3"]: Counter(["o2"])}
        )
        possible_bindings_iter = OCPetriNetSemantics.get_possible_bindings(ocpn, transitions["a"], marking)
        expected_bindings = [
        ]
        self.assert_bindings_equal(possible_bindings_iter, expected_bindings)
        
        marking = OCMarking(
            {places["o1"]: Counter(["o1"]), places["o3"]: Counter(["o1", "o2"])}
        )
        possible_bindings_iter = OCPetriNetSemantics.get_possible_bindings(ocpn, transitions["a"], marking)
        expected_bindings = [
            {
                "order": {"o1"}
            }
        ]
        self.assert_bindings_equal(possible_bindings_iter, expected_bindings)
        
        marking = OCMarking(
            {places["o1"]: Counter(["o1", "o2"]), places["o3"]: Counter(["o1", "o2"])}
        )
        possible_bindings_iter = OCPetriNetSemantics.get_possible_bindings(ocpn, transitions["a"], marking)
        expected_bindings = [
            {
                "order": {"o1"}
            },
            {
                "order": {"o2"}
            }
        ]
        self.assert_bindings_equal(possible_bindings_iter, expected_bindings)
        
        
        

def ocpn_big():
    name = "OCPN_big"
    o1 = OCPetriNet.Place("o1", "order")
    o2 = OCPetriNet.Place("o2", "order")
    o3 = OCPetriNet.Place("o3", "order")
    o4 = OCPetriNet.Place("o4", "order")
    o5 = OCPetriNet.Place("o5", "order")

    i1 = OCPetriNet.Place("i1", "item")
    i2 = OCPetriNet.Place("i2", "item")
    i3 = OCPetriNet.Place("i3", "item")
    i4 = OCPetriNet.Place("i4", "item")
    i5 = OCPetriNet.Place("i5", "item")

    po = OCPetriNet.Transition("po", "place_order")
    si = OCPetriNet.Transition("si", "send_invoice")
    sr = OCPetriNet.Transition("sr", "send_reminder")
    pi = OCPetriNet.Transition("pi", "pick_item")
    pa = OCPetriNet.Transition("pa", "pay_order")
    sh = OCPetriNet.Transition("sh", "ship item")
    co = OCPetriNet.Transition("co", "mark_as_completed")

    a1 = OCPetriNet.Arc(o1, po, "order", is_variable=False)
    o1.add_out_arc(a1)
    po.add_in_arc(a1)

    a2 = OCPetriNet.Arc(i1, po, "item", is_variable=True)
    i1.add_out_arc(a2)
    po.add_in_arc(a2)

    a3 = OCPetriNet.Arc(po, o2, "order", is_variable=False)
    po.add_out_arc(a3)
    o2.add_in_arc(a3)

    a4 = OCPetriNet.Arc(po, i2, "item", is_variable=True)
    po.add_out_arc(a4)
    i2.add_in_arc(a4)

    a5 = OCPetriNet.Arc(o2, si, "order", is_variable=False)
    o2.add_out_arc(a5)
    si.add_in_arc(a5)

    a6 = OCPetriNet.Arc(i2, pi, "item", is_variable=False)
    i2.add_out_arc(a6)
    pi.add_in_arc(a6)

    a7 = OCPetriNet.Arc(si, o3, "order", is_variable=False)
    si.add_out_arc(a7)
    o3.add_in_arc(a7)

    a8 = OCPetriNet.Arc(o3, sr, "order", is_variable=False)
    o3.add_out_arc(a8)
    sr.add_in_arc(a8)

    a9 = OCPetriNet.Arc(sr, o3, "order", is_variable=False)
    sr.add_out_arc(a9)
    o3.add_in_arc(a9)

    a10 = OCPetriNet.Arc(pi, i3, "item", is_variable=False)
    pi.add_out_arc(a10)
    i3.add_in_arc(a10)

    a11 = OCPetriNet.Arc(o3, pa, "order", is_variable=False)
    o3.add_out_arc(a11)
    pa.add_in_arc(a11)

    a12 = OCPetriNet.Arc(i3, sh, "item", is_variable=False)
    i3.add_out_arc(a12)
    sh.add_in_arc(a12)

    a13 = OCPetriNet.Arc(pa, o4, "order", is_variable=False)
    pa.add_out_arc(a13)
    o4.add_in_arc(a13)

    a14 = OCPetriNet.Arc(sh, i4, "item", is_variable=False)
    sh.add_out_arc(a14)
    i4.add_in_arc(a14)

    a15 = OCPetriNet.Arc(o4, co, "order", is_variable=False)
    o4.add_out_arc(a15)
    co.add_in_arc(a15)

    a16 = OCPetriNet.Arc(i4, co, "item", is_variable=True)
    i4.add_out_arc(a16)
    co.add_in_arc(a16)

    a17 = OCPetriNet.Arc(co, o5, "order", is_variable=False)
    co.add_out_arc(a17)
    o5.add_in_arc(a17)

    a18 = OCPetriNet.Arc(co, i5, "item", is_variable=True)
    co.add_out_arc(a18)
    i5.add_in_arc(a18)

    initial_marking = OCMarking({o1: {"order1"}, i1: {"item1", "item2"}})
    final_marking = OCMarking({o5: {"order1"}, i5: {"item1", "item2"}})

    ocpn = OCPetriNet(
        name,
        places=[o1, o2, o3, o4, o5, i1, i2, i3, i4, i5],
        transitions=[po, si, sr, pi, pa, sh, co],
        arcs=[
            a1,
            a2,
            a3,
            a4,
            a5,
            a6,
            a7,
            a8,
            a9,
            a10,
            a11,
            a12,
            a13,
            a14,
            a15,
            a16,
            a17,
            a18,
        ],
        initial_marking=initial_marking,
        final_marking=final_marking,
    )

    return ocpn

def ocpn_multi_start():
    name = "OCPN_multi_start"

    o1 = OCPetriNet.Place("o1", "order")
    o2 = OCPetriNet.Place("o2", "order")
    o3 = OCPetriNet.Place("o3", "order")
    o4 = OCPetriNet.Place("o4", "order")

    a = OCPetriNet.Transition("a", "create_order")

    a1 = OCPetriNet.Arc(o1, a, "order", is_variable=False)
    o1.add_out_arc(a1)
    a.add_in_arc(a1)

    a2 = OCPetriNet.Arc(a, o2, "order", is_variable=False)
    a.add_out_arc(a2)
    o2.add_in_arc(a2)

    a3 = OCPetriNet.Arc(o3, a, "order", is_variable=False)
    o3.add_out_arc(a3)
    a.add_in_arc(a3)

    a4 = OCPetriNet.Arc(a, o4, "order", is_variable=False)
    a.add_out_arc(a4)
    o4.add_in_arc(a4)

    initial_marking = OCMarking({o1: {"order1"}, o3: {"order2"}})
    final_marking = OCMarking({o2: {"order1"}, o4: {"order2"}})

    ocpn = OCPetriNet(
        name,
        places=[o1, o2, o3, o4],
        transitions=[a],
        arcs=[a1, a2, a3, a4],
        initial_marking=initial_marking,
        final_marking=final_marking,
    )
    
    return ocpn

def ocpn_muli_variable_2():
    name = "OCPN_multi_variable"

    p1 = OCPetriNet.Place("p1", "order")
    p2 = OCPetriNet.Place("p2", "order")
    p3 = OCPetriNet.Place("p3", "order")
    p4 = OCPetriNet.Place("p4", "box")
    p5 = OCPetriNet.Place("p5", "box")
    p6 = OCPetriNet.Place("p6", "box")

    a = OCPetriNet.Transition("a", "create_order")

    a1 = OCPetriNet.Arc(p1, a, "order", is_variable=True)
    p1.add_out_arc(a1)
    a.add_in_arc(a1)

    a2 = OCPetriNet.Arc(a, p2, "order", is_variable=True)
    a.add_out_arc(a2)
    p2.add_in_arc(a2)

    a3 = OCPetriNet.Arc(a, p3, "order", is_variable=True)
    a.add_out_arc(a3)
    p3.add_in_arc(a3)
    
    a4 = OCPetriNet.Arc(p4, a, "box", is_variable=True)
    p4.add_out_arc(a4)
    a.add_in_arc(a4)
    
    a5 = OCPetriNet.Arc(a, p5, "box", is_variable=True)
    a.add_out_arc(a5)
    p5.add_in_arc(a5)
    
    a6 = OCPetriNet.Arc(a, p6, "box", is_variable=True)
    a.add_out_arc(a6)
    p6.add_in_arc(a6)



    initial_marking = OCMarking({p1: {"order1"}, p4: {"box1"}})
    final_marking = OCMarking({p2: {"order1"}, p3: {"order1"}, p5: {"box1"}, p6: {"box1"}})

    ocpn = OCPetriNet(
        name,
        places=[p1, p2, p3, p4, p5, p6],
        transitions=[a],
        arcs=[a1, a2, a3, a4, a5, a6],
        initial_marking=initial_marking,
        final_marking=final_marking,
    )
    
    return ocpn

if __name__ == "__main__":
    unittest.main()

import os
import unittest

import pm4py
from pm4py.objects.ocel.obj import OCEL


LOG_PATH = os.path.join("input_data", "ocel", "example_log.jsonocel")


class OcelOlapTest(unittest.TestCase):
    def _load(self):
        return pm4py.read_ocel(LOG_PATH)

    def test_drill_down_splits_types(self):
        ocel = self._load()
        type_col = ocel.object_type_column
        original_types = set(ocel.objects[type_col].unique())

        drilled = pm4py.ocel_drill_down(
            ocel, object_type="element", object_attribute="oattr1"
        )

        self.assertIsInstance(drilled, OCEL)
        new_types = set(drilled.objects[type_col].unique())
        # The drilled log must contain at least one tuple-style sub-type.
        self.assertTrue(
            any(isinstance(t, str) and t.startswith("(element, ") for t in new_types)
        )
        # More distinct types than before (element splits into several).
        self.assertGreater(len(new_types), len(original_types))
        # Relations table is synced with the new object types.
        rel_types = set(drilled.relations[type_col].unique())
        self.assertTrue(
            any(isinstance(t, str) and t.startswith("(element, ") for t in rel_types)
        )
        # Input log was not mutated.
        self.assertEqual(set(ocel.objects[type_col].unique()), original_types)

    def test_drill_down_skips_undefined(self):
        ocel = self._load()
        type_col = ocel.object_type_column
        oid_col = ocel.object_id_column

        # "i4" has NaN oattr1 in the example log; it must retain the
        # original "element" type.
        drilled = pm4py.ocel_drill_down(
            ocel, object_type="element", object_attribute="oattr1"
        )
        i4_rows = drilled.objects[drilled.objects[oid_col] == "i4"]
        self.assertEqual(len(i4_rows), 1)
        self.assertEqual(i4_rows.iloc[0][type_col], "element")

    def test_drill_down_roll_up_roundtrip(self):
        ocel = self._load()
        type_col = ocel.object_type_column

        drilled = pm4py.ocel_drill_down(
            ocel, object_type="element", object_attribute="oattr1"
        )
        rolled = pm4py.ocel_roll_up(drilled, object_type="element")

        self.assertTrue(
            rolled.objects[type_col]
            .reset_index(drop=True)
            .equals(ocel.objects[type_col].reset_index(drop=True))
        )
        self.assertTrue(
            rolled.relations[type_col]
            .reset_index(drop=True)
            .equals(ocel.relations[type_col].reset_index(drop=True))
        )

    def test_unfold_splits_event_type(self):
        ocel = self._load()
        act_col = ocel.event_activity

        unfolded = pm4py.ocel_unfold(
            ocel, event_type="Create Order", object_type="order"
        )

        self.assertIsInstance(unfolded, OCEL)
        self.assertIn(
            "(Create Order, order)",
            set(unfolded.events[act_col].unique()),
        )
        self.assertIn(
            "(Create Order, order)",
            set(unfolded.relations[act_col].unique()),
        )
        # Input log was not mutated.
        self.assertNotIn(
            "(Create Order, order)", set(ocel.events[act_col].unique())
        )

    def test_unfold_fold_roundtrip(self):
        ocel = self._load()
        act_col = ocel.event_activity

        unfolded = pm4py.ocel_unfold(
            ocel, event_type="Create Order", object_type="order"
        )
        folded = pm4py.ocel_fold(
            unfolded, event_type="Create Order", object_type="order"
        )

        self.assertTrue(
            folded.events[act_col]
            .reset_index(drop=True)
            .equals(ocel.events[act_col].reset_index(drop=True))
        )
        self.assertTrue(
            folded.relations[act_col]
            .reset_index(drop=True)
            .equals(ocel.relations[act_col].reset_index(drop=True))
        )

    def test_unfold_with_empty_qualifier_set_is_noop(self):
        ocel = self._load()
        act_col = ocel.event_activity

        unfolded = pm4py.ocel_unfold(
            ocel,
            event_type="Create Order",
            object_type="order",
            qualifiers=[],
        )
        self.assertNotIn(
            "(Create Order, order)",
            set(unfolded.events[act_col].unique()),
        )

    def test_drill_down_invalid_object_type_raises(self):
        ocel = self._load()
        with self.assertRaises(ValueError):
            pm4py.ocel_drill_down(
                ocel,
                object_type="__no_such_type__",
                object_attribute="oattr1",
            )

    def test_drill_down_invalid_attribute_raises(self):
        ocel = self._load()
        with self.assertRaises(ValueError):
            pm4py.ocel_drill_down(
                ocel,
                object_type="element",
                object_attribute="__no_such_attr__",
            )

    def test_drilled_log_still_discovers_ocdfg(self):
        ocel = self._load()
        drilled = pm4py.ocel_drill_down(
            ocel, object_type="element", object_attribute="oattr1"
        )
        # Smoke test: downstream OC-DFG discovery must still work.
        ocdfg = pm4py.discover_ocdfg(drilled)
        self.assertIsNotNone(ocdfg)

    def test_drill_down_roll_up_full_equality(self):
        # Stronger than the column-level round-trip above: the rolled-up
        # OCEL must be fully equal to the original via OCEL.__eq__.
        ocel = self._load()
        drilled = pm4py.ocel_drill_down(
            ocel, object_type="element", object_attribute="oattr1"
        )
        rolled = pm4py.ocel_roll_up(drilled, object_type="element")
        self.assertEqual(rolled, ocel)

    def test_unfold_fold_full_equality(self):
        ocel = self._load()
        unfolded = pm4py.ocel_unfold(
            ocel, event_type="Create Order", object_type="order"
        )
        folded = pm4py.ocel_fold(
            unfolded, event_type="Create Order", object_type="order"
        )
        self.assertEqual(folded, ocel)

    def test_drill_down_is_idempotent(self):
        ocel = self._load()
        once = pm4py.ocel_drill_down(
            ocel, object_type="element", object_attribute="oattr1"
        )
        twice = pm4py.ocel_drill_down(
            once, object_type="element", object_attribute="oattr1"
        )
        # Applying drill-down a second time must be a no-op: the "element"
        # rows left after the first pass have undefined oattr1 and are
        # skipped, and the already-drilled tuple-typed rows no longer match
        # the target type.
        self.assertEqual(twice, once)

    def test_drill_down_preserves_auxiliary_tables(self):
        ocel = self._load()
        drilled = pm4py.ocel_drill_down(
            ocel, object_type="element", object_attribute="oattr1"
        )
        self.assertTrue(drilled.o2o.equals(ocel.o2o))
        self.assertTrue(drilled.e2e.equals(ocel.e2e))
        self.assertTrue(
            drilled.object_changes.equals(ocel.object_changes)
        )

    def test_drill_down_assigns_expected_tuple_values(self):
        # Ground-truth check: verify specific objects receive the exact
        # tuple-typed name derived from their oattr1 value. Without this
        # it would be possible for drill-down to mis-align values with
        # objects (e.g. due to a faulty mask/list assignment).
        ocel = self._load()
        drilled = pm4py.ocel_drill_down(
            ocel, object_type="element", object_attribute="oattr1"
        )
        type_col = drilled.object_type_column
        oid_col = drilled.object_id_column
        indexed = drilled.objects.set_index(oid_col)[type_col].to_dict()
        self.assertEqual(indexed["i1"], "(element, due)")
        self.assertEqual(indexed["i2"], "(element, tre)")
        self.assertEqual(indexed["i3"], "(element, quattro)")
        # i4 has NaN oattr1 and must keep the original type.
        self.assertEqual(indexed["i4"], "element")

    def test_unfold_with_matching_qualifier(self):
        # Positive case for the qualifier filter: the example log uses the
        # empty-string qualifier for every E2O relation, so passing it
        # explicitly must match and rename just like the default None.
        ocel = self._load()
        act_col = ocel.event_activity
        unfolded = pm4py.ocel_unfold(
            ocel,
            event_type="Create Order",
            object_type="order",
            qualifiers=[""],
        )
        self.assertIn(
            "(Create Order, order)",
            set(unfolded.events[act_col].unique()),
        )


if __name__ == "__main__":
    unittest.main()

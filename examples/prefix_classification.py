#!/usr/bin/env python3
import argparse

import pm4py
from pm4py.util import xes_constants
from collections import Counter
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from prefix_feature_extraction import build_prefix_features_next_activity


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Encode every prefix of each trace using the activities and paths up to the "
            "penultimate event, plus time-based features, with the next event as class."
        )
    )
    parser.add_argument(
        "log_path",
        nargs="?",
        default="../tests/input_data/receipt.xes",
        help="Path to the XES log (default: tests/input_data/receipt.xes)",
    )
    parser.add_argument(
        "--activity-key",
        default=xes_constants.DEFAULT_NAME_KEY,
        help=f"Event attribute to use as activity (default: {xes_constants.DEFAULT_NAME_KEY})",
    )
    parser.add_argument(
        "--timestamp-key",
        default=xes_constants.DEFAULT_TIMESTAMP_KEY,
        help=f"Event attribute to use as timestamp (default: {xes_constants.DEFAULT_TIMESTAMP_KEY})",
    )
    parser.add_argument(
        "--show-sample",
        action="store_true",
        help="Print the first 5 feature rows and targets",
    )
    args = parser.parse_args()

    log = pm4py.read_xes(args.log_path, return_legacy_log_object=True)
    (
        feature,
        target,
        activities,
        activity_to_index,
        paths,
        _,
    ) = build_prefix_features_next_activity(
        log, args.activity_key, args.timestamp_key
    )
    if not feature:
        raise SystemExit("No prefixes found in the log.")

    class_counts = Counter(target)
    min_class = min(class_counts.values()) if class_counts else 0
    stratify = target if min_class >= 2 else None
    if stratify is None:
        print(
            "Warning: some classes have < 2 samples; "
            "disabling stratified split."
        )
    X_train, X_test, y_train, y_test = train_test_split(
        feature, target, test_size=0.2, random_state=42, stratify=stratify
    )
    clf = RandomForestClassifier(
        n_estimators=300, random_state=42, n_jobs=-1, class_weight="balanced"
    )
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    print(f"Log path: {args.log_path}")
    print(f"Activity key: {args.activity_key}")
    print(f"Activities: {len(activities)}")
    print(f"Paths: {len(paths)}")
    print(f"Samples (prefixes): {len(feature)}")
    print(f"Feature dimension: {len(activities) + len(paths) + 3}")
    print(f"Target classes: {len(activity_to_index)}")
    print(f"Train size: {len(X_train)}")
    print(f"Test size: {len(X_test)}")
    print(f"Test accuracy: {accuracy:.4f}")

    if args.show_sample:
        print("Sample features (first 5 rows):")
        for row in feature[:5]:
            print(row)
        print("Sample targets (first 5):")
        print(target[:5])


if __name__ == "__main__":
    main()

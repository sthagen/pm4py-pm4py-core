# Coverage report

Measured on 2026-07-17 with coverage.py 7.15.2. Coverage was collected for the entire `pm4py` package with `--source=pm4py`; no files or package paths were omitted. The figures below are statement coverage, including files that were never imported.

## Results

| Measurement | Covered statements | Total statements | Missing statements | Coverage |
| --- | ---: | ---: | ---: | ---: |
| Current tests and examples | 64,403 | 71,387 | 6,984 | **90.22%** |

The final combined result exceeds the 90% target by 0.22 percentage points. Ten source lines carry coverage.py exclusion pragmas; they are reported as excluded lines rather than omitted files.

## Verification

- Custom test runner: 929 tests discovered, 926 passed, 3 skipped, 0 failed, and 0 import failures (100% pass ratio among executed tests).
- Example runner: 139 examples passed, 4 skipped, and 0 failed (100% pass ratio among executed examples).
- The skipped entries require optional services, platform-specific facilities, or interactive environments that were unavailable during this headless run.
- Headless image-viewer warnings and conformance-diagnostic log messages were expected output; neither runner reported a failure.

Current coverage includes 28 focused coverage test modules registered with the existing custom runner. They exercise algorithms, object-centric logs, XES/BPMN I/O, Petri nets and process trees, POWL, Polars analytics, connectors, privacy, serialization, facades, visualizations, and edge/error paths. A small set of existing tests was also updated for current paths, timezone-aware APIs, and the custom runner interface.

## Reproduce

From the repository root, with `coverage` installed:

```bash
export PYTHONPATH="$PWD"
export COVERAGE_FILE="$PWD/.coverage"
export MPLCONFIGDIR=/tmp/pm4py-matplotlib
python -m coverage erase
(cd tests && python -m coverage run --source=pm4py execute_tests.py --pipeline)
(cd examples && python -m coverage run --append --source=pm4py execute_everything.py --pipeline)
python -m coverage report
```

## List the remaining uncovered functions

coverage.py records execution at the statement/line level. To first see which
modules still contain missing statements, read the combined `.coverage` data
produced above with:

```bash
python -m coverage report --show-missing --skip-covered --sort=cover
```

This report lists module paths and missing line numbers, not function names.
With coverage.py 7.15.2, function and method regions are also included in the
JSON report. The completely uncovered functions can therefore be retrieved
from the same combined data as follows:

```bash
python -m coverage json --pretty-print -o coverage.json
python - <<'PY'
import json

with open("coverage.json", encoding="utf-8") as report_file:
    report = json.load(report_file)

uncovered = []
for filename, file_data in report["files"].items():
    for function_name, function_data in file_data.get("functions", {}).items():
        summary = function_data["summary"]

        # The empty name represents statements at module scope, not a function.
        if (
            function_name
            and summary["num_statements"] > 0
            and summary["covered_lines"] == 0
        ):
            uncovered.append(
                (
                    filename,
                    function_data["start_line"],
                    function_name,
                    function_data["missing_lines"],
                )
            )

for filename, start_line, function_name, missing_lines in sorted(uncovered):
    lines = ",".join(str(line) for line in missing_lines)
    print(f"{filename}:{start_line}: {function_name} (missing lines: {lines})")
PY
```

The filter above has a deliberately strict meaning of *uncovered*: the region
has at least one executable statement and none of its statements ran. It
excludes the empty-name region used for module-level statements and functions
with no measurable statements (for example, a body excluded by a coverage
pragma). Class methods are listed with qualified names such as
`ClassName.method_name`.

To also list partially covered functions, replace
`summary["covered_lines"] == 0` with `summary["missing_lines"] > 0`. In that
case, any function with at least one unexecuted statement is included. Both
commands inspect the final combined `.coverage` file, so they should be run
after the test run and the appended example run.

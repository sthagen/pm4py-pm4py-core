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
from typing import Optional, Dict, Any, List, Set, Iterable

import polars as pl

from pm4py.objects.log.util.dataframe_utils import Parameters
from pm4py.util import constants, exec_utils, pandas_utils
from pm4py.util import xes_constants


def _dedupe_preserve_order(values: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _sanitize_feature_name(
    prefix: str, value: Any, used_names: Optional[Set[str]] = None
) -> str:
    sanitized = str(value).encode("ascii", errors="ignore").decode("ascii")
    if not sanitized:
        sanitized = "value"
    base_name = f"{prefix}_{sanitized}"

    if used_names is None:
        return base_name

    candidate = base_name
    suffix = 1
    while candidate in used_names:
        candidate = f"{base_name}__{suffix}"
        suffix += 1
    used_names.add(candidate)
    return candidate


def _scalar_from_lazy(lf: pl.LazyFrame, expr: pl.Expr) -> Any:
    result = lf.select(expr.alias("__scalar")).collect()
    if result.height == 0 or result.width == 0:
        return None
    return result.to_series(0)[0]


def _lazy_schema(lf: pl.LazyFrame) -> pl.Schema:
    return lf.collect_schema()


def _lazy_columns(lf: pl.LazyFrame) -> List[str]:
    return _lazy_schema(lf).names()


def _drop_if_present(lf: pl.LazyFrame, cols: Iterable[str]) -> pl.LazyFrame:
    existing = set(_lazy_columns(lf))
    to_drop = [c for c in cols if c in existing]
    return lf.drop(to_drop) if to_drop else lf


def _unique_internal_name(existing: Set[str], base: str) -> str:
    if base not in existing:
        return base
    i = 1
    while f"{base}__{i}" in existing:
        i += 1
    return f"{base}__{i}"


def _is_numeric_dtype(dtype: pl.DataType) -> bool:
    dtype_str = str(dtype).lower()
    if any(token in dtype_str for token in ("int", "uint", "float")):
        return True
    if dtype_str.startswith("decimal"):
        return True
    if dtype_str.startswith("duration"):
        return True
    if dtype_str == "boolean":
        return True
    return False


def _is_string_dtype(dtype: pl.DataType) -> bool:
    dtype_str = str(dtype).lower()
    return dtype_str in {"utf8", "string"} or dtype_str.startswith("categorical")


def automatic_feature_selection_df(
    df: pl.LazyFrame, parameters: Optional[Dict[Any, Any]] = None
) -> pl.LazyFrame:
    """Selects useful features from a Polars lazyframe for ML purposes."""
    if parameters is None:
        parameters = {}

    schema = _lazy_schema(df)
    available_columns = set(schema.names())

    case_id_key = exec_utils.get_param_value(
        Parameters.CASE_ID_KEY, parameters, constants.CASE_CONCEPT_NAME
    )
    timestamp_key = exec_utils.get_param_value(
        Parameters.TIMESTAMP_KEY,
        parameters,
        xes_constants.DEFAULT_TIMESTAMP_KEY,
    )
    activity_key = exec_utils.get_param_value(
        Parameters.ACTIVITY_KEY, parameters, xes_constants.DEFAULT_NAME_KEY
    )

    default_mandatory = available_columns.intersection(
        {case_id_key, activity_key, timestamp_key}
    )
    mandatory_attributes = exec_utils.get_param_value(
        Parameters.MANDATORY_ATTRIBUTES,
        parameters,
        default_mandatory,
    )
    mandatory_set = set(mandatory_attributes)

    min_different_occ_str_attr = exec_utils.get_param_value(
        Parameters.MIN_DIFFERENT_OCC_STR_ATTR, parameters, 5
    )
    max_different_occ_str_attr = exec_utils.get_param_value(
        Parameters.MAX_DIFFERENT_OCC_STR_ATTR, parameters, 50
    )
    consider_all_attributes = exec_utils.get_param_value(
        Parameters.CONSIDER_ALL_ATTRIBUTES, parameters, True
    )

    other_attributes_to_retain = set()

    total_cases = _scalar_from_lazy(df, pl.col(case_id_key).n_unique())
    total_cases = int(total_cases or 0)

    for col, dtype in schema.items():
        if col == case_id_key:
            continue

        cases_with_value = _scalar_from_lazy(
            df.filter(pl.col(col).is_not_null()),
            pl.col(case_id_key).n_unique(),
        )
        cases_with_value = int(cases_with_value or 0)

        if cases_with_value != total_cases and not consider_all_attributes:
            continue

        if _is_numeric_dtype(dtype):
            other_attributes_to_retain.add(col)
        elif _is_string_dtype(dtype):
            unique_val_count = _scalar_from_lazy(
                df.filter(pl.col(col).is_not_null()),
                pl.col(col).n_unique(),
            )
            unique_val_count = int(unique_val_count or 0)
            if (
                min_different_occ_str_attr
                <= unique_val_count
                <= max_different_occ_str_attr
            ):
                other_attributes_to_retain.add(col)

    attributes_to_retain = mandatory_set.union(other_attributes_to_retain)
    selected_columns = [
        col_name for col_name in schema.names() if col_name in attributes_to_retain
    ]

    return df.select(selected_columns)


def select_number_column(
    df: pl.LazyFrame,
    fea_df: pl.LazyFrame,
    col: str,
    case_id_key: str = constants.CASE_CONCEPT_NAME,
) -> pl.LazyFrame:
    """Adds a numeric column to the feature lazyframe.

    Notes on column duplication:
      * If `fea_df` already contained `col` (e.g., repeated calls / duplicate inputs),
        Polars would create `col_right` during the join. We explicitly drop any prior
        versions first to keep the output schema stable.
      * We also ensure the internal row-number column does not collide with user data.
    """
    fea_df = _drop_if_present(fea_df, [col, f"{col}_right"])

    df_cols = set(_lazy_columns(df))
    row_nr_col = _unique_internal_name(df_cols, "__row_nr")

    df_numeric = (
        df.with_row_count(row_nr_col)
        .select(pl.col(case_id_key), pl.col(col), pl.col(row_nr_col))
        .drop_nulls(subset=[col])
        .group_by(case_id_key)
        .agg(pl.col(col).sort_by(pl.col(row_nr_col)).last().alias(col))
    )

    return (
        fea_df.join(df_numeric, on=case_id_key, how="left", coalesce=True)
        .with_columns(pl.col(col).cast(pl.Float32))
    )


def _collect_categorical_values(
    df: pl.LazyFrame, columns: List[str]
) -> Dict[str, List[Any]]:
    """Collects formatted unique values for the provided categorical columns."""
    collected: Dict[str, List[Any]] = {}
    for col in columns:
        unique_values = (
            df.select(pl.col(col))
            .drop_nulls(subset=[col])
            .unique()
            .collect()
            .get_column(col)
            .to_list()
        )
        formatted = [
            value
            for value in pandas_utils.format_unique(unique_values)
            if value is not None
        ]
        if formatted:
            collected[col] = formatted

    return collected


def _select_string_columns(
    df: pl.LazyFrame,
    fea_df: pl.LazyFrame,
    columns: List[str],
    case_id_key: str,
    count_occurrences: bool,
) -> pl.LazyFrame:
    """Adds one-hot or count encoded columns for the provided categorical attributes.

    This function is designed to be idempotent: running it multiple times with the same
    inputs will overwrite/recompute the same generated feature columns instead of
    creating suffixed duplicates (e.g., `...__1`, `..._right`).
    """
    if not columns:
        return fea_df

    df_schema = _lazy_schema(df)
    available = set(df_schema.names())

    clean_columns = [
        c
        for c in _dedupe_preserve_order(columns)
        if c != case_id_key and c in available
    ]
    if not clean_columns:
        return fea_df

    unique_values_map = _collect_categorical_values(df, clean_columns)
    if not unique_values_map:
        return fea_df

    existing_cols: Set[str] = set(_lazy_columns(fea_df))
    used_names: Set[str] = set(existing_cols)

    agg_exprs: List[pl.Expr] = []
    fill_exprs: List[pl.Expr] = []
    cols_to_drop: Set[str] = set()

    for column, unique_values in unique_values_map.items():
        for value in unique_values:
            # Deterministic base name (no dependency on existing columns).
            base_name = _sanitize_feature_name(column, value)

            # If the feature column already exists, we recompute it (drop first),
            # avoiding `*_right` duplicates from joins.
            if base_name in existing_cols:
                cols_to_drop.add(base_name)
                used_names.discard(base_name)
            if f"{base_name}_right" in existing_cols:
                cols_to_drop.add(f"{base_name}_right")
                used_names.discard(f"{base_name}_right")

            # Ensure uniqueness against the remaining schema + other new features.
            column_name = base_name
            suffix = 1
            while column_name in used_names:
                column_name = f"{base_name}__{suffix}"
                suffix += 1
            used_names.add(column_name)

            comparison = pl.col(column).eq(value)
            if count_occurrences:
                agg_exprs.append(comparison.cast(pl.Int64).sum().alias(column_name))
            else:
                agg_exprs.append(comparison.cast(pl.Int8).max().alias(column_name))

            fill_exprs.append(pl.col(column_name).cast(pl.Float32))

    if cols_to_drop:
        fea_df = _drop_if_present(fea_df, cols_to_drop)

    feature_chunk = (
        df.select([pl.col(case_id_key)] + [pl.col(c) for c in unique_values_map.keys()])
        .group_by(case_id_key)
        .agg(agg_exprs)
        # Materialize all encoded columns in one go to minimize separate joins.
        .with_columns(fill_exprs)
    )

    return fea_df.join(feature_chunk, on=case_id_key, how="left", coalesce=True)


def select_string_column(
    df: pl.LazyFrame,
    fea_df: pl.LazyFrame,
    col: str,
    case_id_key: str = constants.CASE_CONCEPT_NAME,
    count_occurrences: bool = False,
) -> pl.LazyFrame:
    """Adds one-hot or count encoded columns for a categorical attribute."""
    return _select_string_columns(
        df,
        fea_df,
        [col],
        case_id_key=case_id_key,
        count_occurrences=count_occurrences,
    )


def select_string_columns(
    df: pl.LazyFrame,
    fea_df: pl.LazyFrame,
    columns: List[str],
    case_id_key: str = constants.CASE_CONCEPT_NAME,
    count_occurrences: bool = False,
) -> pl.LazyFrame:
    """Adds one-hot or count encoded columns for the provided categorical attributes."""
    return _select_string_columns(
        df,
        fea_df,
        columns,
        case_id_key=case_id_key,
        count_occurrences=count_occurrences,
    )


def get_features_df(
    df: pl.LazyFrame,
    list_columns: List[str],
    parameters: Optional[Dict[Any, Any]] = None,
) -> pl.LazyFrame:
    """Performs automatic feature extraction on a Polars LazyFrame."""
    if parameters is None:
        parameters = {}

    case_id_key = exec_utils.get_param_value(
        Parameters.CASE_ID_KEY, parameters, constants.CASE_CONCEPT_NAME
    )
    add_case_identifier_column = exec_utils.get_param_value(
        Parameters.ADD_CASE_IDENTIFIER_COLUMN, parameters, False
    )
    count_occurrences = exec_utils.get_param_value(
        Parameters.COUNT_OCCURRENCES, parameters, False
    )

    # Avoid duplicate work and join-induced `*_right` columns when the
    # input list contains duplicates.
    list_columns = _dedupe_preserve_order(list_columns)

    fea_df = df.select(pl.col(case_id_key)).unique().sort(case_id_key)

    schema = _lazy_schema(df)
    numeric_columns: List[str] = []
    string_columns: List[str] = []

    for col in list_columns:
        if col == case_id_key or col not in schema:
            continue
        dtype = schema[col]
        if _is_numeric_dtype(dtype):
            numeric_columns.append(col)
        elif _is_string_dtype(dtype):
            string_columns.append(col)

    for col in numeric_columns:
        fea_df = select_number_column(df, fea_df, col, case_id_key=case_id_key)

    fea_df = select_string_columns(
        df,
        fea_df,
        string_columns,
        case_id_key=case_id_key,
        count_occurrences=count_occurrences,
    )

    fea_df = fea_df.sort(case_id_key)
    if not add_case_identifier_column:
        fea_df = fea_df.drop(case_id_key)

    return fea_df


def automatic_feature_extraction_df(
    df: pl.LazyFrame, parameters: Optional[Dict[Any, Any]] = None
) -> pl.LazyFrame:
    """Wrapper that performs automatic feature extraction on a Polars lazyframe."""
    if parameters is None:
        parameters = {}

    case_id_key = exec_utils.get_param_value(
        Parameters.CASE_ID_KEY, parameters, constants.CASE_CONCEPT_NAME
    )
    timestamp_key = exec_utils.get_param_value(
        Parameters.TIMESTAMP_KEY,
        parameters,
        xes_constants.DEFAULT_TIMESTAMP_KEY,
    )

    fea_sel_df = automatic_feature_selection_df(df, parameters=parameters)
    columns = set(_lazy_columns(fea_sel_df))

    columns.discard(case_id_key)
    columns.discard(timestamp_key)

    return get_features_df(fea_sel_df, list(columns), parameters=parameters)

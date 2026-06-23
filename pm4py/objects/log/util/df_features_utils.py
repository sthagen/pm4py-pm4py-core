'''
PM4Py – A Process Mining Library for Python
Copyright (C) 2026 Process Intelligence Solutions GmbH

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
from typing import Optional, Dict, Any, List, Set

import numpy as np
import pandas as pd

from pm4py.objects.log.util.dataframe_utils import Parameters
from pm4py.util import constants, exec_utils, pandas_utils
from pm4py.util import xes_constants


def _sanitize_feature_name(
    prefix: str, value: Any, used_names: Optional[Set[str]] = None
) -> str:
    """
    Build a deterministic feature column name and ensure uniqueness when requested.
    """
    sanitized = (
        str(value)
        .encode("ascii", errors="ignore")
        .decode("ascii")
    )
    if sanitized == "":
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


_NUMERIC_ATTRIBUTE_STATISTICS_SUFFIXES = (
    "LAST",
    "FIRST",
    "MIN",
    "MAX",
    "MEAN",
    "STDEV",
)


def _get_numeric_features_df(
    df: pd.DataFrame,
    numeric_columns: List[str],
    case_id_key: str,
    enable_numeric_attribute_statistics: bool,
) -> pd.DataFrame:
    if not enable_numeric_attribute_statistics:
        return (
            df[[case_id_key] + numeric_columns]
            .copy()
            .groupby(case_id_key)
            .last()
            .reset_index()
        )

    aggregations = {}
    for col in numeric_columns:
        aggregations[f"{col}_LAST"] = pd.NamedAgg(column=col, aggfunc="last")
        aggregations[f"{col}_FIRST"] = pd.NamedAgg(column=col, aggfunc="first")
        aggregations[f"{col}_MIN"] = pd.NamedAgg(column=col, aggfunc="min")
        aggregations[f"{col}_MAX"] = pd.NamedAgg(column=col, aggfunc="max")
        aggregations[f"{col}_MEAN"] = pd.NamedAgg(column=col, aggfunc="mean")
        aggregations[f"{col}_STDEV"] = pd.NamedAgg(
            column=col, aggfunc=lambda values: values.std(ddof=0)
        )

    return (
        df[[case_id_key] + numeric_columns]
        .copy()
        .groupby(case_id_key)
        .agg(**aggregations)
        .reset_index()
    )


def _get_numeric_feature_columns(
    numeric_columns: List[str],
    enable_numeric_attribute_statistics: bool,
) -> List[str]:
    if not enable_numeric_attribute_statistics:
        return numeric_columns
    return [
        f"{col}_{suffix}"
        for col in numeric_columns
        for suffix in _NUMERIC_ATTRIBUTE_STATISTICS_SUFFIXES
    ]


def automatic_feature_selection_df(df, parameters=None):
    """
    Performs an automatic feature selection on dataframes,
    keeping the features useful for ML purposes

    Parameters
    ---------------
    df
        Dataframe
    parameters
        Parameters of the algorithm

    Returns
    ---------------
    featured_df
        Dataframe with only the features that have been selected
    """
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
    activity_key = exec_utils.get_param_value(
        Parameters.ACTIVITY_KEY, parameters, xes_constants.DEFAULT_NAME_KEY
    )

    mandatory_attributes = exec_utils.get_param_value(
        Parameters.MANDATORY_ATTRIBUTES,
        parameters,
        set(df.columns).intersection(
            {case_id_key, activity_key, timestamp_key}
        ),
    )

    min_different_occ_str_attr = exec_utils.get_param_value(
        Parameters.MIN_DIFFERENT_OCC_STR_ATTR, parameters, 5
    )
    max_different_occ_str_attr = exec_utils.get_param_value(
        Parameters.MAX_DIFFERENT_OCC_STR_ATTR, parameters, 50
    )
    consider_all_attributes = exec_utils.get_param_value(
        Parameters.CONSIDER_ALL_ATTRIBUTES, parameters, True
    )

    cols_dtypes = {x: str(df[x].dtype) for x in df.columns}
    other_attributes_to_retain = set()

    no_all_cases = df[case_id_key].nunique()
    for x, y in cols_dtypes.items():
        attr_df = df.dropna(subset=[x])
        this_cases = attr_df[case_id_key].nunique()
        attr_in_all_cases = this_cases == no_all_cases

        # in any case, keep attributes that appears at least once per case
        if attr_in_all_cases or consider_all_attributes:
            if "float" in y or "int" in y:
                # (as in the classic log version) retain always float/int attributes
                other_attributes_to_retain.add(x)
            elif "obj" in y or "str" in y:
                # (as in the classic log version) keep string attributes if they have enough variability, but not too much
                # (that would be hard to explain)
                unique_val_count = df[x].nunique()
                if (
                    min_different_occ_str_attr
                    <= unique_val_count
                    <= max_different_occ_str_attr
                ):
                    other_attributes_to_retain.add(x)
            else:
                # not consider the attribute after this feature selection if it
                # has other types (for example, date)
                pass

    attributes_to_retain = mandatory_attributes.union(
        other_attributes_to_retain
    )

    return df[list(attributes_to_retain)]


def select_number_column(
    df: pd.DataFrame,
    fea_df: pd.DataFrame,
    col: str,
    case_id_key=constants.CASE_CONCEPT_NAME,
    enable_numeric_attribute_statistics=False,
) -> pd.DataFrame:
    """
    Extract a column for the features dataframe for the given numeric attribute

    Parameters
    --------------
    df
        Dataframe
    fea_df
        Feature dataframe
    col
        Numeric column
    case_id_key
        Case ID key
    enable_numeric_attribute_statistics
        If True, extract last, first, min, max, mean, and stdev columns.

    Returns
    --------------
    fea_df
        Feature dataframe (desidered output)
    """
    numeric_columns = [col]
    df_numeric = _get_numeric_features_df(
        df,
        numeric_columns,
        case_id_key,
        enable_numeric_attribute_statistics,
    )
    numeric_feature_columns = _get_numeric_feature_columns(
        numeric_columns, enable_numeric_attribute_statistics
    )
    fea_df = fea_df.merge(
        df_numeric, on=[case_id_key], how="left", suffixes=("", "_y")
    )
    fea_df[numeric_feature_columns] = fea_df[numeric_feature_columns].astype(
        np.float32
    )
    return fea_df


def select_string_column(
    df: pd.DataFrame,
    fea_df: pd.DataFrame,
    col: str,
    case_id_key=constants.CASE_CONCEPT_NAME,
    count_occurrences=False,
) -> pd.DataFrame:
    """
    Extract N columns (for N different attribute values; hotencoding) for the features dataframe for the given string attribute

    Parameters
    --------------
    df
        Dataframe
    fea_df
        Feature dataframe
    col
        String column
    case_id_key
        Case ID key
    count_occurrences
        If True, count the number of occurrences of the attribute value in each case.
        If False (default), use binary encoding (1 if present, 0 if not present)

    Returns
    --------------
    fea_df
        Feature dataframe (desidered output)
    """
    # Filter out None values once
    df_filtered = df[[case_id_key, col]].dropna(subset=[col])
    existing_cols = set(fea_df.columns)

    if count_occurrences:
        # Use crosstab for efficient counting
        crosstab = pd.crosstab(df_filtered[case_id_key], df_filtered[col])
        # Rename columns efficiently while avoiding duplicates
        rename_map = {
            original: _sanitize_feature_name(col, original, existing_cols)
            for original in crosstab.columns
        }
        crosstab = crosstab.rename(columns=rename_map)
        # Merge once with all columns
        fea_df = fea_df.merge(
            crosstab, left_on=case_id_key, right_index=True, how="left"
        )
        # Fill NaN and convert to float32 for all new columns at once
        new_cols = list(rename_map.values())
        if new_cols:
            fea_df[new_cols] = fea_df[new_cols].astype(np.float32)
    else:
        # Use pivot_table for binary encoding - much faster than loop
        # Create a dummy column for aggregation
        df_filtered = df_filtered.copy()
        df_filtered["_dummy"] = 1
        cases_with_values = df_filtered[case_id_key].unique()

        # Get unique values
        unique_vals = pandas_utils.format_unique(df_filtered[col].unique())
        unique_vals = [v for v in unique_vals if v is not None]

        if len(unique_vals) > 0:
            # Create pivot table
            pivot = df_filtered.pivot_table(
                index=case_id_key,
                columns=col,
                values="_dummy",
                aggfunc="max",
            )

            # Rename columns (ensuring uniqueness when sanitization collides)
            rename_map = {
                original: _sanitize_feature_name(col, original, existing_cols)
                for original in pivot.columns
            }
            pivot = pivot.rename(columns=rename_map)

            # Merge once with all columns
            fea_df = fea_df.merge(
                pivot, left_on=case_id_key, right_index=True, how="left"
            )
            # Fill NaN only for cases having at least one value and convert to float32
            new_cols = list(rename_map.values())
            if new_cols:
                mask = (
                    fea_df[case_id_key].isin(cases_with_values)
                    if case_id_key in fea_df.columns
                    else None
                )
                for col_name in new_cols:
                    if col_name in fea_df.columns:
                        if mask is not None:
                            fea_df.loc[mask, col_name] = (
                                fea_df.loc[mask, col_name].fillna(0)
                            )
                        fea_df[col_name] = fea_df[col_name].astype(np.float32)

    return fea_df


def get_features_df(
    df: pd.DataFrame,
    list_columns: List[str],
    parameters: Optional[Dict[Any, Any]] = None,
) -> pd.DataFrame:
    """
    Given a dataframe and a list of columns, performs an automatic feature extraction

    Parameters
    ---------------
    df
        Dataframe
    list_column
        List of column to consider in the feature extraction
    parameters
        Parameters of the algorithm, including:
        - Parameters.CASE_ID_KEY: the case ID
        - Parameters.COUNT_OCCURRENCES: if True, count occurrences of string attributes instead of binary encoding
        - Parameters.ENABLE_NUMERIC_ATTRIBUTE_STATISTICS: if True, extract last, first, min, max, mean, and stdev for numeric attributes

    Returns
    ---------------
    fea_df
        Feature dataframe (desidered output)
    """
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
    enable_numeric_attribute_statistics = exec_utils.get_param_value(
        Parameters.ENABLE_NUMERIC_ATTRIBUTE_STATISTICS, parameters, False
    )

    # Start with unique case IDs
    unique_cases = sorted(pandas_utils.format_unique(df[case_id_key].unique()))
    fea_df = pandas_utils.instantiate_dataframe({case_id_key: unique_cases})

    # Separate columns by type for batch processing
    string_columns = []
    numeric_columns = []

    for col in list_columns:
        dtype_str = str(df[col].dtype)
        if "obj" in dtype_str or "str" in dtype_str:
            string_columns.append(col)
        elif "float" in dtype_str or "int" in dtype_str:
            numeric_columns.append(col)

    # Process numeric columns (can be done more efficiently in batch)
    if numeric_columns:
        df_numeric = _get_numeric_features_df(
            df,
            numeric_columns,
            case_id_key,
            enable_numeric_attribute_statistics,
        )
        numeric_feature_columns = _get_numeric_feature_columns(
            numeric_columns, enable_numeric_attribute_statistics
        )
        # Merge once for all numeric columns
        fea_df = fea_df.merge(df_numeric, on=case_id_key, how="left")
        # Convert all numeric columns to float32 at once
        fea_df[numeric_feature_columns] = fea_df[
            numeric_feature_columns
        ].astype(np.float32)

    # Process string columns one by one (still needed due to hot encoding)
    for col in string_columns:
        fea_df = select_string_column(
            df, fea_df, col, case_id_key=case_id_key, count_occurrences=count_occurrences
        )

    # Sort and optionally remove case ID
    fea_df = fea_df.sort_values(case_id_key)
    if not add_case_identifier_column:
        del fea_df[case_id_key]

    return fea_df


def automatic_feature_extraction_df(
    df: pd.DataFrame, parameters: Optional[Dict[Any, Any]] = None
) -> pd.DataFrame:
    """
    Performs an automatic feature extraction given a dataframe

    Parameters
    --------------
    df
        Dataframe
    parameters
        Parameters of the algorithm, including:
        - Parameters.CASE_ID_KEY: the case ID
        - Parameters.MIN_DIFFERENT_OCC_STR_ATTR
        - Parameters.MAX_DIFFERENT_OCC_STR_ATTR

    Returns
    --------------
    fea_df
        Dataframe with the features
    """
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
    columns = set(fea_sel_df.columns)

    if case_id_key in columns:
        columns.remove(case_id_key)

    if timestamp_key in columns:
        columns.remove(timestamp_key)

    return get_features_df(fea_sel_df, list(columns), parameters=parameters)

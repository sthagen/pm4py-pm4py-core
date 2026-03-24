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

import os
import sqlite3
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

import pandas as pd
from pm4py.util.dt_parsing.variants import strpfromiso
from pm4py.util import exec_utils, pandas_utils


class Parameters(Enum):
    """Enum container for optional *apply* parameters."""

    HISTORY_DB_PATH = "history_db_path"


# -----------------------------------------------------------------------------
# Firefox-internal transition type constants → human-readable labels
# -----------------------------------------------------------------------------
VISIT_TYPE_MAP = {
    0: "LINK",  # Followed a hyperlink (default navigation)
    1: "TYPED",  # URL typed in the address bar (or pasted & Go)
    2: "BOOKMARK",  # Visit launched from a bookmark
    3: "EMBED",  # Automatically loaded in an embedded context (img/iframe)
    4: "REDIRECT_PERM",  # 301 permanent redirect target
    5: "REDIRECT_TEMP",  # 302/307 temporary redirect target
    6: "DOWNLOAD",  # Explicit file download
    7: "FRAMED_LINK",  # Link inside a frameset / iframe clicked by user
    8: "RELOAD",  # Page reload (F5 / Ctrl-R)
    9: "USER_TYPED",  # Legacy typed constant (alias of 1)
}


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def apply(parameters: Optional[Dict[Any, str]] = None) -> pd.DataFrame:
    """Extract an event log from one or more *places.sqlite* files.

    The function can be pointed **either** at a specific *places.sqlite* file
    **or** at the *Profiles* directory containing multiple profile folders. If
    a directory is given, a separate case identifier is generated for every
    profile found.

    Attributes created per event (column → description)
    ---------------------------------------------------
    * **case:concept:name** – Identifier of the Firefox profile folder (or
      "DEFAULT" when a single DB path is supplied). Serves as *case ID* in
      process-mining terminology.

    * **concept:name** – Canonicalised URL path (protocol/query stripped).
      Acts as *activity label* for each event.

    * **time:timestamp** – Python ``datetime`` converted from Firefox's PRTime
      (microseconds since Unix epoch).

    * **complete_url** – Full URL including scheme and query string, suitable
      when the exact navigation target is important.

    * **domain** – Registered domain portion of the URL; helps grouping visits
      by site.

    * **url_wo_parameters** – Same as *concept:name* but kept separately for
      convenience when the activity label gets renamed downstream.

    * **title** – Page title stored by Firefox (from ``moz_places.title``).
      Note: may be *NULL* for some automatic loads or download links.

    * **visit_type** – Raw integer from ``moz_historyvisits.visit_type``.
      Referential value for advanced analysis.

    * **visit_type_desc** – Human-friendly label mapped from ``visit_type`` via
      :data:`VISIT_TYPE_MAP` (e.g., "TYPED", "BOOKMARK", "RELOAD").

    * **session_id** – Numeric identifier grouping visits that happened within
      the same browser session (i.e., between Firefox startups).

    * **from_visit** – ``visit_id`` of the *referrer* visit inside the same
      database – enables reconstruction of click chains within a tab.

    * **visit_count_place** – Cumulative counter how often the *place* (URL)
      has been visited overall up to the current record.

    * **typed** – ``True`` when the user explicitly typed/pasted the address
      (``moz_places.typed > 0``). Often correlates with intentional navigations.

    * **frecency** – Firefox’s scoring metric combining *frequency* and
      *recency*; higher numbers indicate pages likely to appear as top results
      in the address bar.

    * **guid** – Stable 12-character base-62 GUID uniquely identifying the
      *place* entry – useful as a surrogate key when merging logs.

    Returns
    -------
    pandas.DataFrame
        Chronologically sorted event log ready for process-mining libraries.
    """
    if parameters is None:
        parameters = {}

    # ------------------------------------------------------------------
    # Resolve DB location (explicit path or default Windows profile dir)
    # ------------------------------------------------------------------
    history_db_path = exec_utils.get_param_value(
        Parameters.HISTORY_DB_PATH,
        parameters,
        os.path.join(
            os.path.expanduser("~"),
            "AppData",
            "Roaming",
            "Mozilla",
            "Firefox",
            "Profiles",
        ),
    )

    # Collect one (file path, profile name) tuple per profile
    if os.path.isdir(history_db_path):
        profiles = [
            (os.path.join(history_db_path, p, "places.sqlite"), p)
            for p in os.listdir(history_db_path)
        ]
    else:
        profiles = [(history_db_path, "DEFAULT")]

    profiles = [p for p in profiles if os.path.exists(p[0])]

    # ------------------------------------------------------------------
    # Unified SQL pulling all the attributes listed above
    # ------------------------------------------------------------------
    QUERY = (
        "SELECT "
        "p.url, v.visit_date, p.title, v.visit_type, v.session, v.from_visit, "
        "p.visit_count, p.typed, p.frecency, p.guid "
        "FROM moz_historyvisits v JOIN moz_places p ON v.place_id = p.id"
    )

    events = []

    for db_path, profile_name in profiles:
        try:
            conn = sqlite3.connect(db_path)
            curs = conn.cursor()
            curs.execute(QUERY)

            rows = curs.fetchall()
            for (
                url,
                visit_date,
                title,
                visit_type,
                session_id,
                from_visit,
                visit_count_place,
                typed,
                frecency,
                guid,
            ) in rows:
                # Convert micro-second PRTime → datetime (naïve, local time)
                ts = strpfromiso.fix_naivety(datetime.fromtimestamp(visit_date / 1_000_000))

                ev = {
                    "case:concept:name": profile_name,
                    "concept:name": url.split("//")[-1].split("?")[0].replace(",", ""),
                    "complete_url": url,
                    "domain": url.split("//")[-1].split("/")[0],
                    "url_wo_parameters": url.split("//")[-1].split("?")[0],
                    "time:timestamp": ts,
                    "title": title,
                    "visit_type": visit_type,
                    "visit_type_desc": VISIT_TYPE_MAP.get(visit_type, "UNKNOWN"),
                    "session_id": session_id,
                    "from_visit": from_visit,
                    "visit_count_place": visit_count_place,
                    "typed": bool(typed),
                    "frecency": frecency,
                    "guid": guid,
                }

                if ev["case:concept:name"].strip() and ev["concept:name"].strip():
                    events.append(ev)
        finally:
            curs.close()
            conn.close()

    # ------------------------------------------------------------------
    # Convert list → DataFrame and impose stable, chronological ordering
    # ------------------------------------------------------------------
    df = pandas_utils.instantiate_dataframe(events)

    if not df.empty:
        df = pandas_utils.insert_index(df, "@@index", copy_dataframe=False, reset_index=False)
        df = df.sort_values(["time:timestamp", "@@index"], kind="mergesort")
        df["@@case_index"] = df.groupby("case:concept:name", sort=False).ngroup()
        df = df.sort_values(["@@case_index", "time:timestamp", "@@index"], kind="mergesort")

    return df

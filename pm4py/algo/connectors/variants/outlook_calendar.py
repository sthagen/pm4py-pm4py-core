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
from typing import Optional, Dict, Any, List
from pm4py.util import exec_utils, pandas_utils
from enum import Enum
from pm4py.algo.connectors.util import mail as mail_utils
from pm4py.util.dt_parsing.variants import strpfromiso
import pandas as pd
from datetime import datetime, timedelta
import importlib.util
import traceback


class Parameters(Enum):
    EMAIL_USER = "email_user"
    CALENDAR_ID = "calendar_id"
    INCLUDE_REMINDERS = "include_reminders"


# Values used by Outlook that identify a cancelled meeting (olMeetingCanceled)
# See: https://learn.microsoft.com/office/vba/api/outlook.olmeetingstatus
OL_MEETING_CANCELED = 5


def _add_event(
    buffer: list,
    conversation_id: str,
    subject: str,
    timestamp: datetime,
    activity: str,
):
    """Helper to push a single event dict on *buffer* with minimal syntax."""

    buffer.append(
        {
            "case:concept:name": conversation_id,
            "case:subject": subject,
            "time:timestamp": timestamp,
            "concept:name": activity,
        }
    )


def apply(parameters: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    Extracts the history of the calendar events (creation, update, start, end)
    in a Pandas dataframe from the local Outlook instance running on the current computer.

    CASE ID (case:concept:name) => identifier of the meeting
    ACTIVITY (concept:name) => one between: Meeting Created, Last Change of Meeting, Meeting Started, Meeting Completed,
    Meeting Cancelled, Meeting Reminder Fired
    TIMESTAMP (time:timestamp) => the timestamp of the event
    case:subject => the subject of the meeting

    Returns
    -------
    dataframe
        Pandas dataframe
    """
    if parameters is None:
        parameters = {}

    calendar_id = exec_utils.get_param_value(Parameters.CALENDAR_ID, parameters, 9)
    email_user = exec_utils.get_param_value(Parameters.EMAIL_USER, parameters, None)
    include_reminders = exec_utils.get_param_value(
        Parameters.INCLUDE_REMINDERS, parameters, True
    )

    # Connect to local Outlook instance / profile
    calendar = mail_utils.connect(email_user, calendar_id)

    # Optional progress bar if *tqdm* is on the system
    progress = None
    if importlib.util.find_spec("tqdm"):
        from tqdm.auto import tqdm

        progress = tqdm(total=len(calendar.Items), desc="extracting calendar items")

    events: List[Dict[str, Any]] = []

    for item in calendar.Items:
        try:
            conversation_id = str(item.ConversationID)
            subject = str(item.Subject)

            creation_time = strpfromiso.fix_naivety(
                datetime.fromtimestamp(item.CreationTime.timestamp())
            )
            last_mod_time = strpfromiso.fix_naivety(
                datetime.fromtimestamp(item.LastModificationTime.timestamp())
            )
            start_time = strpfromiso.fix_naivety(
                datetime.fromtimestamp(item.Start.timestamp())
            )
            end_time = strpfromiso.fix_naivety(
                datetime.fromtimestamp(item.Start.timestamp() + 60 * item.Duration)
            )

            # ── canonical 4 events ──────────────────────────────────────────────
            _add_event(events, conversation_id, subject, creation_time, "Meeting Created")

            if last_mod_time != creation_time:
                _add_event(
                    events,
                    conversation_id,
                    subject,
                    last_mod_time,
                    "Last Change of Meeting",
                )

            _add_event(events, conversation_id, subject, start_time, "Meeting Started")
            _add_event(events, conversation_id, subject, end_time, "Meeting Completed")

            # ── newly added events ─────────────────────────────────────────────
            # a) Meeting cancelled (status 5) – timestamped at *LastModificationTime*
            meeting_status = getattr(item, "MeetingStatus", None)
            if meeting_status == OL_MEETING_CANCELED:
                _add_event(events, conversation_id, subject, last_mod_time, "Meeting Cancelled")

            # b) Reminder – fire time = start_time − ReminderMinutesBeforeStart
            if include_reminders and getattr(item, "ReminderSet", False):
                minutes_before = getattr(item, "ReminderMinutesBeforeStart", None)
                if isinstance(minutes_before, int):
                    reminder_time = start_time - timedelta(minutes=minutes_before)
                    # Only add if the computed time is not in the future: the reminder has *already* triggered
                    if reminder_time <= datetime.now(tz=reminder_time.tzinfo):
                        _add_event(
                            events,
                            conversation_id,
                            subject,
                            reminder_time,
                            "Meeting Reminder Fired",
                        )

        except BaseException:
            traceback.print_exc()
            # swallow – keep going but still show failure in console

        if progress is not None:
            progress.update()

    if progress is not None:
        progress.close()

    # ── turn list → DataFrame & canonical ordering ───────────────────────────
    df = pandas_utils.instantiate_dataframe(events)
    df = pandas_utils.insert_index(df, "@@index", copy_dataframe=False, reset_index=False)
    df = df.sort_values(["time:timestamp", "@@index"])
    df["@@case_index"] = df.groupby("case:concept:name", sort=False).ngroup()
    df = df.sort_values(["@@case_index", "time:timestamp", "@@index"])

    return df

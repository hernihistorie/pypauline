from __future__ import annotations # Needed to fix https://github.com/jcrist/msgspec/issues/924

import datetime
from typing import NewType
import msgspec
from msgspec import field

class Event(msgspec.Struct, kw_only=True, frozen=True, tag_field="event_type", tag=True):
    """Base class for events."""

    event_version: int = 1
    event_timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)

class TestEvent(Event, kw_only=True, frozen=True):
    test_data: str

PyHXCFERunId = NewType('PyHXCFERunId', str)

class PyHXCFEERunStarted(Event, frozen=True):
    """
    Event triggered when pyhxcfe starts processing.
    """
    pyhxcfe_run_id: PyHXCFERunId
    command: list[str]
    user: str | None
    host: str | None
    start_time: str
    git_revision: str


class FloppyDiskCaptureDirectoryConverted(Event, frozen=True):
    """
    Event triggered when a floppy disk capture has been converted
    using hxcfe.
    """
    pyhxcfe_run_id: PyHXCFERunId
    capture_directory: str
    success: bool
    formats: list[str]

class FloppyInfoFromName(msgspec.Struct, kw_only=True, frozen=True):
    datetime: str
    operator: str
    item_identifier: str
    drive: str
    dump_index: int

    hh_asset_id: int | None
    """
    Parsed from item identifier if it is prefixed with "rh" or "hh".
    """

class FloppyInfoFromXML(msgspec.Struct, kw_only=True, frozen=True):
    file_size: int
    number_of_tracks: int
    number_of_sides: int
    format: str
    sector_per_track: int
    sector_size: int
    bitrate: int
    rpm: int
    crc32: int

class FloppyInfoFromIMD(msgspec.Struct, kw_only=True, frozen=True):
    parsing_success: bool
    tracks: int | None
    modes: list[str] | None
    error_count: int | None
    parsing_errors: str | None


class FloppyDiskCaptureSummarized(Event, frozen=True):
    """
    Event triggered when a floppy disk capture has been summarized.
    """
    pyhxcfe_run_id: PyHXCFERunId
    capture_directory: str

    name_info: FloppyInfoFromName
    xml_info: FloppyInfoFromXML
    imd_info: FloppyInfoFromIMD


class PyHXCFEERunFinished(Event, frozen=True):
    """
    Event triggered when pyhxcfe finishes processing.
    """
    pyhxcfe_run_id: PyHXCFERunId

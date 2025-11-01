import datetime
from dataclasses import dataclass, field,
from typing import NewType

@dataclass(kw_only=True)
class Event:
    """Base class for events."""

    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)

@dataclass
class TestEvent(Event):
    test_data: str

PyHXCFERunId = NewType('PyHXCFERunId', str)

@dataclass
class PyHXCFEERunStarted(Event):
    """
    Event triggered when pyhxcfe starts processing.
    """
    pyhxcfe_run_id: PyHXCFERunId
    command: list[str]
    user: str | None
    host: str | None
    start_time: str
    git_revision: str


@dataclass
class FloppyDiskCaptureDirectoryConverted(Event):
    """
    Event triggered when a floppy disk capture has been converted
    using hxcfe.
    """
    pyhxcfe_run_id: PyHXCFERunId
    capture_directory: str
    success: bool
    formats: list[str]

@dataclass
class FloppyInfoFromName():
    datetime: str
    operator: str
    item_identifier: str
    drive: str
    dump_index: int

    hh_asset_id: int | None
    """
    Parsed from item identifier if it is prefixed with "rh" or "hh".
    """

@dataclass
class FloppyInfoFromXML():
    file_size: int
    number_of_tracks: int
    number_of_sides: int
    format: str
    sector_per_track: int
    sector_size: int
    bitrate: int
    rpm: int
    crc32: int

@dataclass
class FloppyInfoFromIMD():
    parsing_success: bool
    tracks: int | None
    modes: list[str] | None
    error_count: int | None
    parsing_errors: str | None


@dataclass
class FloppyDiskCaptureSummarized(Event):
    """
    Event triggered when a floppy disk capture has been summarized.
    """
    pyhxcfe_run_id: PyHXCFERunId
    capture_directory: str

    name_info: FloppyInfoFromName
    xml_info: FloppyInfoFromXML
    imd_info: FloppyInfoFromIMD


@dataclass
class PyHXCFEERunFinished(Event):
    """
    Event triggered when pyhxcfe finishes processing.
    """
    pyhxcfe_run_id: PyHXCFERunId

from dataclasses import dataclass
from typing import NewType

@dataclass
class Event:
    """Base class for events."""

PyHXCFERunId = NewType('PyHXCFERunId', str)

@dataclass
class PyHXCFEERunStarted(Event):
    """
    Event triggered when pyhxcfe starts processing.
    """
    pyhxcfe_run_id: PyHXCFERunId
    command: list[str]
    host: str
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


class EventStore:
    def emit_event(self, event: Event) -> None:
        """Emit an event (currently just prints to stdout)."""
        print(f"Event emitted: {event}")

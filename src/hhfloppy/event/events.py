from __future__ import annotations # Needed to fix https://github.com/jcrist/msgspec/issues/924

import datetime
from typing import Literal, NewType, Union
import uuid

import msgspec
from msgspec import field

from .datatypes import HHFLOPPY_EVENT_DATA_CLASS_UNION, FloppyInfoFromIMD, FloppyInfoFromName, FloppyInfoFromXML, HHFloppyTaggedStruct

class Event(HHFloppyTaggedStruct, kw_only=True, frozen=True):
    """Base class for events."""

    event_version: int = 5
    event_timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
    event_id: uuid.UUID = field(default_factory=uuid.uuid7)

class TestEvent(Event, kw_only=True, frozen=True):
    test_data: str

PyHXCFERunId = NewType('PyHXCFERunId', uuid.UUID)

# Add e.g. info.json here once implemented
FloppyDiskCaptureIDSource = Literal['hashed_directory_name']

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
    floppy_disk_capture_id: uuid.UUID
    floppy_disk_capture_id_source: FloppyDiskCaptureIDSource
    floppy_disk_capture_directory: str
    success: bool
    formats: list[str]

class FloppyDiskCaptureSummarized(Event, frozen=True):
    """
    Event triggered when a floppy disk capture has been summarized.
    """
    pyhxcfe_run_id: PyHXCFERunId
    floppy_disk_capture_id: uuid.UUID
    floppy_disk_capture_id_source: FloppyDiskCaptureIDSource
    floppy_disk_capture_directory: str

    name_info: FloppyInfoFromName
    xml_info: FloppyInfoFromXML
    imd_info: FloppyInfoFromIMD


class PyHXCFEERunFinished(Event, frozen=True):
    """
    Event triggered when pyhxcfe finishes processing.
    """
    pyhxcfe_run_id: PyHXCFERunId

HHFLOPPY_EVENT_CLASS_UNION = Union[
    TestEvent,
    PyHXCFEERunStarted,
    FloppyDiskCaptureDirectoryConverted,
    FloppyDiskCaptureSummarized,
    PyHXCFEERunFinished,
]

# For sanity, try to make a decoder

event_decoder = msgspec.json.Decoder(HHFLOPPY_EVENT_CLASS_UNION | HHFLOPPY_EVENT_DATA_CLASS_UNION)

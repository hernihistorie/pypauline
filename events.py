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


@dataclass
class FloppyDiskCaptureProcessed(Event):
    """
    Event triggered when a floppy disk capture has been processed
    using hxcfe.
    """
    pyhxcfe_run_id: PyHXCFERunId
    capture_path: str
    success: bool
    formats: list[str]

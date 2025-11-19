import uuid
import subprocess
from pathlib import Path

FLOPPY_DISK_CAPTURE_FILENAME_UUID_NAMESPACE = uuid.UUID('019a9df8-6505-7032-923f-12a806f8bdbf')

def get_git_version() -> str:
    """Get the current git revision, with -dirty suffix if there are uncommitted changes."""
    try:
        # Get the short commit hash
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).parent
        )
        version = result.stdout.strip()
        
        # Check if there are uncommitted changes
        result = subprocess.run(
            ['git', 'diff-index', '--quiet', 'HEAD', '--'],
            cwd=Path(__file__).parent
        )
        
        # If exit code is non-zero, there are uncommitted changes
        if result.returncode != 0:
            version += '-dirty'
        
        return version
    except (subprocess.CalledProcessError, FileNotFoundError):
        # If git is not available or not a git repo, return unknown
        return 'unknown'

def floppy_disk_capture_filename_to_id(filename: str) -> uuid.UUID:
    """Convert a floppy disk capture filename to a UUID based on its name."""
    # Use UUID5 with the DNS namespace and the filename as the name
    return uuid.uuid5(namespace=FLOPPY_DISK_CAPTURE_FILENAME_UUID_NAMESPACE, name=filename)

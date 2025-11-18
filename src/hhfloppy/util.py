import subprocess
from pathlib import Path


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

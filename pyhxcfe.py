# Goal of the script: Run the HxCFloppyEmulator software on disk captures made with Pauline
# and output information about the floppy, sectors, formatting, contents in JSON.

from os import mkdir
import os
import subprocess
import shlex
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import click
from tqdm import tqdm

HXCFE_BINARY_PATH = Path('/home/sanqui/ha/HxCFloppyEmulator/build/hxcfe')
WORKERS=12

FORMATS = [
    ('GENERIC_XML', 'xml'),
    ('RAW_IMG', 'img'),
    ('RAW_LOADER', 'img'),
    # ('HXC_HFE', 'hfe'),
    # ('HXC_HFEV3', 'hfe'),
    # ('HXC_EXTHFE', 'hfe'),
    # ('ZXSPECTRUM_FDI', 'fdi'),
    # ('ZXSPECTRUM_TRD', 'trd'),
    # ('ZXSPECTRUM_SCL', 'scl'),
    ('PNG_IMAGE', 'png'),
    ('PNG_STREAM_IMAGE', 'png'),
    ('PNG_DISK_IMAGE', 'png'),
]

def process_directory(hxcfe_binary_path: Path, floppy_dir: Path, floppy_subdir: Path):
    parsed_dir = floppy_dir / (floppy_subdir.name + "_parsed")
    if not os.path.exists(parsed_dir):
        mkdir(parsed_dir)

    first_file = next(floppy_subdir.iterdir())
    cmd: list[str] = [
        hxcfe_binary_path.as_posix(),
        '-finput:' + shlex.quote(str(first_file)),
    ]

    for fmt, extension in FORMATS:
        cmd.append('-conv:' + fmt)
        cmd.append('-foutput:' + shlex.quote(str(parsed_dir / (f'{fmt}.{extension}'))))

    with open(parsed_dir / 'stdout.txt', 'w') as f_stdout, open(parsed_dir / 'stderr.txt', 'w') as f_stderr:
        subprocess.run(
            args=cmd,
            stdout=f_stdout,
            stderr=f_stderr,
            check=True,
            env=dict(os.environ, LD_LIBRARY_PATH=hxcfe_binary_path.parent.as_posix())
        )
    
    return floppy_subdir.name


@click.command()
@click.argument(
    'disk_captures_dir',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path)
)
@click.option(
    '--hxcfe-binary-path',
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    default=HXCFE_BINARY_PATH,
    help='Path to hxcfe binary'
)
@click.option(
    '--workers',
    default=WORKERS,
    type=int,
    help='Maximum number of parallel workers'
)
def main(disk_captures_dir: Path, hxcfe_binary_path: Path, workers: int):
    """Process disk captures with HxCFloppyEmulator.
    
    DISK_CAPTURES_DIR: Directory containing floppy disk captures to process
    """

    dirs: list[tuple[Path, Path]] = []

    for floppy_dir in disk_captures_dir.iterdir():
        for floppy_subdir in floppy_dir.iterdir():
            if floppy_subdir.name.endswith("_parsed"):
                continue

            dirs.append((floppy_dir, floppy_subdir))

    dirs.sort()

    with tqdm(total=len(dirs)) as pbar:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [
                ex.submit(process_directory, hxcfe_binary_path, *dir) for dir in dirs
            ]
            for future in as_completed(futures):
                try:
                    result = future.result()
                    pbar.write(f"Completed {result}")
                except Exception as ex:
                    pbar.write(f"Failed to complete: {type(ex).__name__}: {ex}")
                pbar.update(1)


if __name__ == '__main__':
    main()

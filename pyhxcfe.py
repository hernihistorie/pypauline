# Goal of the script: Run the HxCFloppyEmulator software on disk captures made with Pauline
# and output information about the floppy, sectors, formatting, contents in JSON.

from os import mkdir
import os
from sys import argv
import subprocess
import shlex
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

HXCFE_BINARY_PATH = '/home/sanqui/pauline/HxCFloppyEmulator_soft_beta/HxCFloppyEmulator_soft/HxCFloppyEmulator_Software/Windows_x64/hxcfe.exe'

MAX_WORKERS=12

FORMATS = [
    ('GENERIC_XML', 'xml'),
    ('RAW_IMG', 'img'),
    ('RAW_LOADER', 'img'),
    ('HXC_HFE', 'hfe'),
    ('HXC_HFEV3', 'hfe'),
    ('HXC_EXTHFE', 'hfe'),
    ('PNG_IMAGE', 'png'),
    ('PNG_STREAM_IMAGE', 'png'),
    ('PNG_DISK_IMAGE', 'png'),
]

def process_directory(floppy_dir: Path, floppy_subdir: Path):
    parsed_dir = floppy_dir / (floppy_subdir.name + "_parsed")
    if not os.path.exists(parsed_dir):
        mkdir(parsed_dir)

    first_file = next(floppy_subdir.iterdir())
    cmd = [
        HXCFE_BINARY_PATH,
        '-finput:' + shlex.quote(str(first_file)),
    ]

    for fmt, extension in FORMATS:
        cmd.append('-conv:' + fmt)
        cmd.append('-foutput:' + shlex.quote(str(parsed_dir / (f'{fmt}.{extension}'))))

    with open(parsed_dir / 'stdout.txt', 'w') as f_stdout, open(parsed_dir / 'stderr.txt', 'w') as f_stderr:
        subprocess.run(cmd, stdout=f_stdout, stderr=f_stderr, check=True)
    
    return floppy_subdir.name


disk_caputres_dir = Path(argv[1])

dirs = []

for floppy_dir in disk_caputres_dir.iterdir():
    for floppy_subdir in floppy_dir.iterdir():
        if floppy_subdir.name.endswith("_parsed"):
            continue

        dirs.append((floppy_dir, floppy_subdir))

dirs.sort()

with tqdm(total=len(dirs)) as pbar:
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(process_directory, *dir) for dir in dirs]
        for future in as_completed(futures):
            try:
                result = future.result()
                pbar.write(f"Completed {result}")
            except Exception as ex:
                pbar.write(f"Failed to complete: {type(ex).__name__}: {ex}")
            pbar.update(1)


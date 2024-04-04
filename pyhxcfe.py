# Goal of the script: Run the HxCFloppyEmulator software on disk captures made with Pauline
# and output information about the floppy, sectors, formatting, contents in JSON.

from os import mkdir
import os
from sys import argv
import subprocess
import shlex
from pathlib import Path

from tqdm import tqdm

HXCFE_BINARY_PATH = '/home/sanqui/pauline/HxCFloppyEmulator_soft_beta (1)/HxCFloppyEmulator_soft/HxCFloppyEmulator_Software/Windows_x64/hxcfe.exe'


FORMATS = [
    ('GENERIC_XML', 'xml'),
    ('RAW_IMG', 'img'),
    ('RAW_LOADER', 'img'),
    ('BMP_IMAGE', 'bmp'),
    ('BMP_STREAM_IMAGE', 'bmp'),
    ('BMP_DISK_IMAGE', 'bmp')
]

disk_caputres_dir = Path(argv[1])

dirs = []

for floppy_dir in disk_caputres_dir.iterdir():
    for floppy_subdir in floppy_dir.iterdir():
        if floppy_subdir.name.endswith("_parsed"):
            continue

        dirs.append((floppy_dir, floppy_subdir))

for floppy_dir, floppy_subdir in tqdm(dirs):
    tqdm.write(f"Parsing {floppy_subdir.name}")

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

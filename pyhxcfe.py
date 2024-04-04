# Goal of the script: Run the HxCFloppyEmulator software on disk captures made with Pauline
# and output information about the floppy, sectors, formatting, contents in JSON.

from os import mkdir
import os
import subprocess
import shlex
from pathlib import Path

HXCFE_BINARY_PATH = '/home/sanqui/pauline/HxCFloppyEmulator_soft_beta (1)/HxCFloppyEmulator_soft/HxCFloppyEmulator_Software/Windows_x64/hxcfe.exe'


FORMATS = [
    ('GENERIC_XML', 'xml'),
    ('BMP_IMAGE', 'bmp'),
    ('BMP_STREAM_IMAGE', 'bmp'),
    ('BMP_DISK_IMAGE', 'bmp')
]

disk_caputres_dir = Path('disk_captures')

for floppy_dir in disk_caputres_dir.iterdir():
    for floppy_subdir in floppy_dir.iterdir():
        if floppy_subdir.name.endswith("_parsed"):
            continue

        print(f"Parsing {floppy_subdir.name}")

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
        subprocess.run(cmd, check=True)

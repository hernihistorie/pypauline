from dataclasses import dataclass
from pathlib import Path
import shlex
import shutil
import sys
import tempfile
import re
import subprocess

HXCFE_BINARY_PATH = '/home/sanqui/pauline/HxCFloppyEmulator_soft_beta/HxCFloppyEmulator_soft/HxCFloppyEmulator_Software/Windows_x64/hxcfe.exe'

RE_HXC_TRACK = re.compile(r'track(\d+)\.(\d+)\.hxcstream')

A8RAWCONV_BINARY_PATH = Path('deps/a8rawconv-0.95/a8rawconv.exe')

@dataclass
class TrackAndSide():
    track: int
    side: int


def parse_hxc_filename(filename: str) -> TrackAndSide:
    match = RE_HXC_TRACK.match(filename)
    if not match:
        raise ValueError(f"Error: Could not parse filename {filename}")

    return TrackAndSide(track=int(match.group(1)), side=int(match.group(2)))

def hxcfe_convert(first_filepath: Path, convert_format: str, output_filepath: Path):
    cmd = [
        HXCFE_BINARY_PATH,
        '-finput:' + shlex.quote(str(first_filepath)),
    ]

    cmd.append('-conv:' + convert_format)
    cmd.append('-foutput:' + shlex.quote(str(output_filepath)))

    # with open(parsed_dir / 'stdout.txt', 'w') as f_stdout, open(parsed_dir / 'stderr.txt', 'w') as f_stderr:
    subprocess.run(cmd, check=True)

def conv_atari8bit(dirpath: Path):
    floppyname = dirpath.parent.name
    with tempfile.TemporaryDirectory(delete=False) as tmpdirname:
        tmpdirpath = Path(tmpdirname)
        print("tmp dir path", tmpdirpath)

        filepaths = sorted(dirpath.glob('*.hxcstream'))
        # match "track80.0.hxcstream" with regex
        last = parse_hxc_filename(filepaths[-1].name)
        if last.track > 40:
            # High density floppy dump, but Atari 8-bit didn't use those
            # we have to remove odd tracks
            remove_odd_tracks = True
        else:
            remove_odd_tracks = False
        
        for filepath in filepaths:
            track_and_side = parse_hxc_filename(filepath.name)
            if remove_odd_tracks and track_and_side.track % 2 == 1:
                continue
            if track_and_side.side == 1:
                # Atari 8-bit only used side 0
                continue
            
            track = track_and_side.track
            if remove_odd_tracks:
                track //= 2
            
            # copy to temp dir

            
            shutil.copy(filepath, tmpdirpath / f'track{track:02}.{track_and_side.side}.hxcstream')

        print("Converting to HFE format...")
        hxcfe_convert(
            first_filepath=tmpdirpath / 'track00.0.hxcstream',
            convert_format='HXC_HFE',
            output_filepath=tmpdirpath / 'floppy.hfe'
        )

        print("Converting to SCP format...")
        hxcfe_convert(
            first_filepath=tmpdirpath / 'floppy.hfe',
            convert_format='SCP_FLUX_STREAM',
            output_filepath=tmpdirpath / 'floppy.scp'
        )

        print("Running a8rawconv to convert to ATR format...")
        outpath = f'out/{floppyname}.atr'
        cmd = [
            str(A8RAWCONV_BINARY_PATH),
            '-tpi', '96', # density - 48 or 96
            '-g', '40,1', # number of tracks, number of sides
            str(tmpdirpath / 'floppy.scp'),
            outpath
        ]

        subprocess.run(cmd, check=True)

        print(f"Done: {outpath}")
        

        # print(f"Converting {filepath}")
        # tmpfilepath = tmpdirpath / filepath.name        

def conv_dir(dirpath: Path):
    for item in dirpath.iterdir():
        if not item.is_dir():
            continue
        
        # Find subdirectories
        subdirs = list(item.iterdir())
        subdirs = [d for d in subdirs if d.is_dir()]
        
        if not subdirs:
            print(f"Warning: No subdirectories found in {item}")
            continue
        
        if len(subdirs) > 1:
            print(f"Warning: Multiple subdirectories found in {item}, expected only one")
            continue
            
        subdir = subdirs[0]
        print(f"Processing {subdir}...")
        conv_atari8bit(subdir)

def main():
    print(sys.argv)
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <dirpath>")
        sys.exit(1)

    if not A8RAWCONV_BINARY_PATH.exists():
        sys.exit("Please download a8rawconv from https://forums.atariage.com/applications/core/interface/file/attachment.php?id=365615 and place it in deps/a8rawconv-0.3")
    
    dirpath = Path(sys.argv[1])
    conv_dir(dirpath)

if __name__ == '__main__':
    main()
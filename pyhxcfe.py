# Goal of the script: Run the HxCFloppyEmulator software on disk captures made with Pauline
# and output information about the floppy, sectors, formatting, contents in JSON.

from dataclasses import dataclass
from os import mkdir
import os
import shutil
import subprocess
import shlex
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
import uuid

import click
from jinja2 import Environment, FileSystemLoader
from tqdm import tqdm
from events import Event, EventStore, FloppyDiskCaptureDirectoryConverted, FloppyDiskCaptureSummarized, FloppyInfoFromIMD, FloppyInfoFromXML, PyHXCFEERunFinished, PyHXCFEERunStarted, PyHXCFERunId
from python_imd.imd import Disk
from util import get_git_version

HXCFE_BINARY_PATH = Path('/home/sanqui/ha/HxCFloppyEmulator/build/hxcfe')
WORKERS=16

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
    ('IMD_IMG', 'imd'),
    ('PNG_IMAGE', 'png'),
    ('PNG_STREAM_IMAGE', 'png'),
    ('PNG_DISK_IMAGE', 'png'),
]

def convert_disk_capture_directory(pyhxcfe_run_id: PyHXCFERunId, hxcfe_binary_path: Path, floppy_subdir: Path) -> list[Event]:
    parsed_dir = floppy_subdir.parent / (floppy_subdir.name + "_parsed_wip")
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

    os.rename(parsed_dir, floppy_subdir.parent / (floppy_subdir.name + "_parsed"))

    return [
        FloppyDiskCaptureDirectoryConverted(
            pyhxcfe_run_id=pyhxcfe_run_id,
            capture_directory=floppy_subdir.name,
            success=True,
            formats=[fmt for fmt, _ in FORMATS]
        )
    ]


def parse_generic_xml(xml_path: Path) -> FloppyInfoFromXML:
    """Parse GENERIC_XML.xml file and extract key information."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    layout = root.find('layout')
    assert layout
    
    file_size = root.findtext('file_size')
    number_of_track = layout.findtext('number_of_track')
    number_of_side = layout.findtext('number_of_side')
    format_text = layout.findtext('format')
    sector_per_track = layout.findtext('sector_per_track')
    sector_size = layout.findtext('sector_size')
    bitrate = layout.findtext('bitrate')
    rpm = layout.findtext('rpm')
    crc32 = layout.findtext('crc32')
    
    assert file_size is not None
    assert number_of_track is not None
    assert number_of_side is not None
    assert format_text is not None
    assert sector_per_track is not None
    assert sector_size is not None
    assert bitrate is not None
    assert rpm is not None
    assert crc32 is not None
    
    return FloppyInfoFromXML(
        file_size=int(file_size),
        number_of_tracks=int(number_of_track),
        number_of_sides=int(number_of_side),
        format=format_text,
        sector_per_track=int(sector_per_track),
        sector_size=int(sector_size),
        bitrate=int(bitrate),
        rpm=int(rpm),
        crc32=int(crc32, 16),
    )
    


def parse_imd_file(imd_path: Path) -> FloppyInfoFromIMD:
    """Parse IMD file and extract key information."""
    try:
        disk = Disk.from_file(str(imd_path))
        
        # Collect statistics
        mode_names: list[str] = []
        errors = 0
        
        for track in disk.tracks:
            if track.mode.name not in mode_names:
                mode_names.append(track.mode.name)

            for record in track.sector_data_records:
                if hasattr(record, 'record_type') and hasattr(record.record_type, 'has_error'):
                    if record.record_type.has_error:
                        errors += 1
        
        return FloppyInfoFromIMD(
            parsing_success=True,
            tracks=len(disk.tracks),
            modes=mode_names,
            error_count=errors,
            parsing_errors=None
        )
    except Exception as e:
        return FloppyInfoFromIMD(
            parsing_success=False,
            tracks=None,
            modes=None,
            error_count=None,
            parsing_errors=f'Error: {str(e)}',
        )

@dataclass
class FloppySummaryRow():
    summary_event: FloppyDiskCaptureSummarized
    floppy_subdir: Path

def process_converted_disks(pyhxcfe_run_id: PyHXCFERunId, disk_captures_dir: Path, output_file: Path):
    """Gather data from converted disks and generate HTML summary."""

    floppy_summaries: list[FloppySummaryRow] = []

    # Collect all processed directories
    for floppy_dir in sorted(disk_captures_dir.iterdir()):
        if not floppy_dir.is_dir():
            continue
            
        for floppy_subdir in sorted(floppy_dir.iterdir()):
            if not floppy_subdir.name.endswith("_parsed"):
                continue
            
            xml_info: FloppyInfoFromXML = parse_generic_xml(floppy_subdir / "GENERIC_XML.xml")
            
            imd_info: FloppyInfoFromIMD = parse_imd_file(floppy_subdir / "IMD_IMG.imd")
            
            summary_event = FloppyDiskCaptureSummarized(
                pyhxcfe_run_id=pyhxcfe_run_id,
                capture_directory=floppy_subdir.name,
                info_from_xml=xml_info,
                info_from_imd=imd_info
            )

            floppy_summary_row = FloppySummaryRow(
                summary_event=summary_event,
                floppy_subdir=floppy_subdir
            )

            floppy_summaries.append(floppy_summary_row)

    # Generate HTML using Jinja2
    template_dir = Path(__file__) .parent / 'templates'
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('summary.html')
    
    html = template.render(
        total_floppies=len(floppy_summaries),
        generated_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        source_directory=str(disk_captures_dir),
        floppy_summaries=floppy_summaries
    )
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    
    print(f"\nHTML summary generated: {output_file}")
    print(f"Total floppies: {len(floppy_summaries)}")


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
@click.option(
    '--redo',
    flag_value='redo',
    help='Redo processing of already finished directories'
)
@click.option(
    '--summary-only',
    is_flag=True,
    help='Only generate HTML summary without processing'
)
@click.option(
    '--output',
    type=click.Path(path_type=Path),
    default=None,
    help='Output path for HTML summary (default: summary_TIMESTAMP.html in disk captures dir)'
)
def main(disk_captures_dir: Path, hxcfe_binary_path: Path, workers: int, redo: bool, 
         summary_only: bool, output: Path | None):
    """Process disk captures with HxCFloppyEmulator.
    
    DISK_CAPTURES_DIR: Directory containing floppy disk captures to process
    """

    event_store = EventStore()

    run_id = PyHXCFERunId(str(uuid.uuid7()))

    event_store.emit_event(PyHXCFEERunStarted(
        pyhxcfe_run_id=run_id,
        command=sys.argv,
        host=os.uname().nodename,
        start_time=datetime.now().isoformat(),
        git_revision=get_git_version()
    ))

    if not summary_only:
        print(f"Using {workers} workers.")

        dirs: list[Path] = []
        finished_dirs: list[Path] = []

        for floppy_dir in disk_captures_dir.iterdir():
            if not floppy_dir.is_dir():
                continue
            for floppy_subdir in floppy_dir.iterdir():
                if floppy_subdir.name.endswith("_parsed"):
                    continue

                if floppy_subdir.name.endswith("_parsed_wip"):
                    shutil.rmtree(floppy_subdir)
                    continue

                if os.path.isdir(floppy_subdir.parent / (floppy_subdir.name + "_parsed")):
                    if redo:
                        shutil.rmtree(floppy_subdir.parent / (floppy_subdir.name + "_parsed"))
                    else:
                        finished_dirs.append(floppy_subdir)
                        continue

                dirs.append(floppy_subdir)

        dirs.sort()
        print(f"Found {len(dirs)} directories to process, {len(finished_dirs)} already finished.")

        results: list[Event] = []

        with tqdm(total=len(dirs)) as pbar:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futures = [
                    ex.submit(convert_disk_capture_directory, run_id, hxcfe_binary_path, dir) for dir in dirs
                ]
                for future in as_completed(futures):
                    try:
                        result: list[Event] = future.result()
                        pbar.write(f"Completed {result}")
                        results.extend(result)
                    except Exception as ex:
                        pbar.write(f"Failed to complete: {type(ex).__name__}: {ex}")
                    pbar.update(1)
        
        for event in results:
            event_store.emit_event(event)

    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = disk_captures_dir / f"summary_{timestamp}.html"
    process_converted_disks(run_id, disk_captures_dir, output)

    event_store.emit_event(PyHXCFEERunFinished(
        pyhxcfe_run_id=run_id
    ))

if __name__ == '__main__':
    main()

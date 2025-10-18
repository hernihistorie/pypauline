# Goal of the script: Run the HxCFloppyEmulator software on disk captures made with Pauline
# and output information about the floppy, sectors, formatting, contents in JSON.

from os import mkdir
import os
import shutil
import subprocess
import shlex
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import xml.etree.ElementTree as ET
from datetime import datetime

import click
from tqdm import tqdm

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

def process_directory(hxcfe_binary_path: Path, floppy_subdir: Path):
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

    return floppy_subdir.name


def parse_generic_xml(xml_path: Path) -> dict:
    """Parse GENERIC_XML.xml file and extract key information."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        layout = root.find('layout')
        if layout is None:
            return None
        
        info = {
            'interface_mode': root.findtext('interface_mode', ''),
            'file_size': root.findtext('file_size', ''),
            'number_of_track': layout.findtext('number_of_track', ''),
            'number_of_side': layout.findtext('number_of_side', ''),
            'format': layout.findtext('format', ''),
            'sector_per_track': layout.findtext('sector_per_track', ''),
            'sector_size': layout.findtext('sector_size', ''),
            'bitrate': layout.findtext('bitrate', ''),
            'rpm': layout.findtext('rpm', ''),
            'crc32': layout.findtext('crc32', ''),
        }
        return info
    except Exception as e:
        return {'error': str(e)}


def generate_html_summary(disk_captures_dir: Path, output_file: Path):
    """Generate HTML summary of all processed floppies."""
    
    floppies = []
    
    # Collect all processed directories
    for floppy_dir in sorted(disk_captures_dir.iterdir()):
        if not floppy_dir.is_dir():
            continue
            
        for floppy_subdir in sorted(floppy_dir.iterdir()):
            if not floppy_subdir.name.endswith("_parsed"):
                continue
            
            xml_path = floppy_subdir / "GENERIC_XML.xml"
            if not xml_path.exists():
                continue
            
            info = parse_generic_xml(xml_path)
            if info is None:
                continue
            
            # Extract metadata from directory name
            parent_name = floppy_subdir.parent.name
            
            # Get relative paths to PNG files
            png_image = floppy_subdir / "PNG_IMAGE.png"
            png_stream = floppy_subdir / "PNG_STREAM_IMAGE.png"
            png_disk = floppy_subdir / "PNG_DISK_IMAGE.png"
            
            floppies.append({
                'parent_dir': parent_name,
                'parsed_dir': floppy_subdir.name,
                'xml_path': xml_path,
                'png_image': png_image if png_image.exists() else None,
                'png_stream': png_stream if png_stream.exists() else None,
                'png_disk': png_disk if png_disk.exists() else None,
                **info
            })
    
    # Generate HTML
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Floppy Disk Processing Summary</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        th {
            background-color: #4CAF50;
            color: white;
            padding: 12px;
            text-align: left;
            position: sticky;
            top: 0;
        }
        td {
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .error {
            color: red;
            font-style: italic;
        }
        .summary {
            background-color: white;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        code {
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
        }
        .png-links {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .png-links a {
            padding: 4px 8px;
            background-color: #2196F3;
            color: white;
            text-decoration: none;
            border-radius: 3px;
            font-size: 0.85em;
        }
        .png-links a:hover {
            background-color: #0b7dda;
        }
    </style>
</head>
<body>
    <h1>Floppy Disk Processing Summary</h1>
    <div class="summary">
        <p><strong>Total processed floppies:</strong> """ + str(len(floppies)) + """</p>
        <p><strong>Generated:</strong> """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        <p><strong>Source directory:</strong> <code>""" + str(disk_captures_dir) + """</code></p>
    </div>
    <table>
        <thead>
            <tr>
                <th>Parent Directory</th>
                <th>PNG Images</th>
                <th>Interface Mode</th>
                <th>File Size</th>
                <th>Tracks</th>
                <th>Sides</th>
                <th>Format</th>
                <th>Sectors/Track</th>
                <th>Sector Size</th>
                <th>Bitrate</th>
                <th>RPM</th>
                <th>CRC32</th>
            </tr>
        </thead>
        <tbody>
"""
    
    for floppy in floppies:
        if 'error' in floppy:
            html += f"""            <tr>
                <td>{floppy['parent_dir']}</td>
                <td colspan="11" class="error">Error: {floppy['error']}</td>
            </tr>
"""
        else:
            # Build PNG links
            png_links_html = '<div class="png-links">'
            if floppy.get('png_image'):
                rel_path = floppy['png_image'].relative_to(disk_captures_dir)
                png_links_html += f'<a href="{rel_path}" target="_blank">Image</a>'
            if floppy.get('png_stream'):
                rel_path = floppy['png_stream'].relative_to(disk_captures_dir)
                png_links_html += f'<a href="{rel_path}" target="_blank">Stream</a>'
            if floppy.get('png_disk'):
                rel_path = floppy['png_disk'].relative_to(disk_captures_dir)
                png_links_html += f'<a href="{rel_path}" target="_blank">Disk</a>'
            png_links_html += '</div>'
            
            html += f"""            <tr>
                <td>{floppy['parent_dir']}</td>
                <td>{png_links_html}</td>
                <td>{floppy['interface_mode']}</td>
                <td>{floppy['file_size']}</td>
                <td>{floppy['number_of_track']}</td>
                <td>{floppy['number_of_side']}</td>
                <td>{floppy['format']}</td>
                <td>{floppy['sector_per_track']}</td>
                <td>{floppy['sector_size']}</td>
                <td>{floppy['bitrate']}</td>
                <td>{floppy['rpm']}</td>
                <td>{floppy['crc32']}</td>
            </tr>
"""
    
    html += """        </tbody>
    </table>
</body>
</html>
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\nHTML summary generated: {output_file}")
    print(f"Total floppies: {len(floppies)}")


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
    '--generate-summary',
    is_flag=True,
    help='Generate HTML summary after processing'
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
         generate_summary: bool, summary_only: bool, output: Path | None):
    """Process disk captures with HxCFloppyEmulator.
    
    DISK_CAPTURES_DIR: Directory containing floppy disk captures to process
    """

    print(f"Using {workers} workers.")

    # If summary-only, just generate the summary and exit
    if summary_only:
        if output is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = disk_captures_dir / f"summary_{timestamp}.html"
        generate_html_summary(disk_captures_dir, output)
        return

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

    with tqdm(total=len(dirs)) as pbar:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [
                ex.submit(process_directory, hxcfe_binary_path, dir) for dir in dirs
            ]
            for future in as_completed(futures):
                try:
                    result = future.result()
                    pbar.write(f"Completed {result}")
                except Exception as ex:
                    pbar.write(f"Failed to complete: {type(ex).__name__}: {ex}")
                pbar.update(1)

    # Generate HTML summary if requested
    if generate_summary:
        if output is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = disk_captures_dir / f"summary_{timestamp}.html"
        generate_html_summary(disk_captures_dir, output)


if __name__ == '__main__':
    main()

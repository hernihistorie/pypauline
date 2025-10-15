#!/usr/bin/env python

import asyncio
from dataclasses import dataclass, field
import time
import datetime
import re
import tqdm
import asyncssh
from pathlib import Path
import getpass

import click
import websockets

import tkinter as tk
from PIL import Image, ImageTk
import io
import threading
from queue import Queue

NUM_TRACKS = 82
#DUMP_TIME = 440
#DUMP_TIME = 100
DUMP_TIME = 840

INVENTORY_CODE="hh"

class TrackImageViewer:
    def __init__(self):
        self.image_queue = Queue()
        self.thread = threading.Thread(target=self._run_viewer, daemon=True)
        self.thread.start()

    def _run_viewer(self):
        root = tk.Tk()
        root.title("Track Viewer")
        root.minsize(800, 600)
        self.label = tk.Label(root)
        self.label.pack()
        
        def update_image():
            try:
                while not self.image_queue.empty():
                    image_data = self.image_queue.get_nowait()
                    image = Image.open(io.BytesIO(image_data))
                    # Resize image to reasonable dimensions if needed
                    # image.thumbnail((800, 600))
                    try:
                        photo = ImageTk.PhotoImage(image)
                        self.label.configure(image=photo)
                        self.label.image = photo  # Keep a reference!
                    except OSError:
                        pass
            finally:
                root.after(50, update_image)  # Schedule next update
        
        update_image()
        root.mainloop()

    def show_image(self, image_data):
        self.image_queue.put(image_data)

@dataclass
class Pauline():
    address: str
    config: str | None = None
    drives: list[str] = field(default_factory=lambda: ['unkfd0', 'unkfd1', 'unkfd2', 'unkfd3', 'unkfd4', 'unkfd5'])
    
    def __post_init__(self):
        self.pending_tasks = set()
        # self.image_viewer = TrackImageViewer()

    async def connect(self):
        print("Connecting to websockets...")
        self.ws = await websockets.connect(f"ws://{self.address}:8080")
        self.ws_image = await websockets.connect(f"ws://{self.address}:8081")

        print("Connecting to ssh...")
        self.ssh = await asyncssh.connect(
            self.address,
            username="pauline",
            password="pauline",
            known_hosts=None
        )

        result = await self.ssh.run("uname -s", check=True)
        assert result.stdout
        assert result.stdout.strip() == "Linux"

        config_result = await self.ssh.run("cat /home/pauline/Settings/drives.script", check=True)
        assert isinstance(config_result.stdout, str)
        self.config = config_result.stdout
        
        # parse config
        for line in self.config.split('\n'):
            line = line.strip()
            if line.startswith('set'):
                var = line.split(' ')[1]
                val = ' '.join(line.split(' ')[2:])

                if var == 'DRIVE_0_DESCRIPTION':
                    self.drives[0] = val.strip('"')
                elif var == 'DRIVE_1_DESCRIPTION':
                    self.drives[1] = val.strip('"')
                elif var == 'DRIVE_2_DESCRIPTION':
                    self.drives[2] = val.strip('"')
                elif var == 'DRIVE_3_DESCRIPTION':
                    self.drives[3] = val.strip('"')
                elif var == 'DRIVE_4_DESCRIPTION':
                    self.drives[4] = val.strip('"')
                elif var == 'DRIVE_5_DESCRIPTION':
                    self.drives[5] = val.strip('"')

        print(f"Connected. Parsed drives from config: {self.drives}")

    async def send_ws(self, msg: str) -> None:
        await self.ws.send(msg)
        print(f">>> {msg}")
    
    async def return_heads(self, drives: list[int]):
        print("Returning heads...")
        for floppy_index in drives:
            await self.send_ws(f"recalibrate {floppy_index}")
            await asyncio.sleep(4.5)
        
        print("Returned heads")
        await self.send_ws(f"sound 2200 100")
        await asyncio.sleep(0.1)
        await self.send_ws(f"sound 2200 100")
        await asyncio.sleep(0.1)
        await self.send_ws(f"sound 2300 200")
    
    async def upload_to_nas(self):
        print("Uploading onto NAS")

        # Get list of subdirectories in Disks_Captures
        try:
            result = await self.ssh.run(
                "find /home/pauline/Disks_Captures -mindepth 1 -maxdepth 1 -type d",
                check=True
            )
            if not result.stdout:
                print("No directories to upload")
                return
            
            subdirs = [d.strip() for d in result.stdout.strip().split('\n') if d.strip()]
            
            if not subdirs:
                print("No directories to upload")
                return
            
            # Create the destination directory first
            await self.ssh.run("mkdir -p /home/pauline/Disks_Captures_Done")
            
            # Upload each subdirectory with progress bar
            bar = tqdm.tqdm(total=len(subdirs), desc='Uploading')
            for subdir in subdirs:
                subdir_name = subdir.split('/')[-1]
                bar.set_description(f'Uploading {subdir_name}')
                
                try:
                    result = await self.ssh.run(
                        f"scp -P 7722 -r {subdir} dumper@nas.herniarchiv.cz:dumps/pauline2/Disks_Captures/",
                        check=True
                    )
                    
                    if result.stderr and "update_known_hosts: hostfile_replace_entries failed" in str(result.stderr):
                        # This happens on Pauline because the filesystem doesn't support links.
                        # bar.write(f"Note: update_known_hosts failed for {subdir_name}, but this is not a problem.")
                        pass
                    
                    bar.write(f"Uploaded {subdir_name}")
                    
                    await self.ssh.run(f"mv {subdir} /home/pauline/Disks_Captures_Done/")
                    # bar.write(f"Moved {subdir_name} to Disks_Captures_Done")
                    bar.update(1)
                    
                except asyncssh.process.ProcessError as e:
                    bar.write(f"Warning: Failed to upload {subdir_name}: {e}")
                    bar.update(1)
                    continue
            
            bar.close()
            print("Done uploading")
            
        except asyncssh.process.ProcessError:
            print("Warning: Uploading to NAS failed.  Does Pauline have internet connection?")
            return

    async def save_track_image(self, output_dir: Path, filename_base: str, track: int, side: int) -> None:
        try:
            # Set 2 second timeout for the entire image retrieval operation
            async with asyncio.timeout(2.0):
                await self.ws_image.send("get_image")
                image_data = await self.ws_image.recv()
                
                # Show image in viewer
                # self.image_viewer.show_image(image_data)
                
                # Ensure the images directory exists
                image_dir = output_dir / f"{filename_base}_images"
                image_dir.mkdir(exist_ok=True)
                
                # Save the image
                image_path = image_dir / f"track{track}.{side}.png"
                with open(image_path, "wb") as f:
                    f.write(image_data)
        except TimeoutError:
            print(f"Timeout while getting image for track {track}.{side}")
        except Exception as e:
            print(f"Error saving image for track {track}.{side}: {e}")

    async def _save_track_image_wrapped(self, *args, **kwargs):
        try:
            await self.save_track_image(*args, **kwargs)
        except Exception as e:
            print(f"Background task error: {e}")
        finally:
            self.pending_tasks.remove(asyncio.current_task())

    async def run_batch(self, floppy_names: list[str], operator: str | None = None):
        await self.connect()

        bar_outer = tqdm.tqdm(total=len(floppy_names), desc='floppy')
        bar_outer.update(0)
        last_floppy_name = None
        for floppy_index, (floppy_name, drive_name) in enumerate(zip(floppy_names, self.drives)):
            if floppy_name == '-':
                bar_outer.write(f"Skipping floppy in drive {floppy_index}")
                bar_outer.update(1)
                continue
            elif floppy_name == '+':
                assert isinstance(last_floppy_name, str)
                floppy_name = INVENTORY_CODE + str(int(last_floppy_name.removeprefix(INVENTORY_CODE)) + 1)
            elif floppy_name.lower() == 'clean':
                bar_outer.write(f"Please insert cleaning floppy in drive {drive_name} (index {floppy_index}), then press RETURN")
                input()
                dump_time=400
            else:
                dump_time = DUMP_TIME
            
            num_str = f"{floppy_index + 1}/{len(floppy_names)}"
            datetime_str = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            if not floppy_name.startswith(INVENTORY_CODE):
                floppy_name = f"{INVENTORY_CODE}{floppy_name}"
            operator_name = operator if operator is not None else getpass.getuser()
            filename = f"{datetime_str}_{operator_name}_{floppy_name}_{drive_name}"
            bar_outer.write(f"Dumping {floppy_name} ({num_str}): {filename}")

            # TODO first check with the last sector to see if reading isn't bad

            await self.send_ws(f"sound {1000 + 100*floppy_index} 100")
            await self.send_ws("set MACINTOSH_GCR_MODE 0")
            await self.send_ws("index_to_dump 0")
            await self.send_ws(f"dump_time {dump_time}")
            try:
                # static int readdisk(int drive, int dump_start_track,int dump_max_track,int dump_start_side,int dump_max_side,int high_res_mode,int doublestep,int ignore_index,int spy, char * name, char * comment, char * comment2, int start_index, int incmode, char * driveref, char * operator)
                await self.send_ws(f'dump {floppy_index} 0 {NUM_TRACKS} 0 1 0 0 0 0 "{filename}" "" 1 AUTO_INDEX_NAME "" "" ""')
                bar = tqdm.tqdm(total=NUM_TRACKS, desc='track', leave=False)
                bar.update(0)
                while True:
                    message = await self.ws.recv()
                    bar.write(f"[{num_str}] <<< {message.strip()}")
                    # use regex to extract 37 and 0 from ...t_rh6791-0001/track37.0.hxcstream
                    match = re.search(r'/track(\d+)\.(\d+)\.hxcstream', message)
                    if match:
                        track = int(match.group(1))
                        side = int(match.group(2))
                        bar.update(0.5)
                        # Save the track image after each track is completed
                        # Create background task for image saving
                        # task = asyncio.create_task(
                        #     self._save_track_image_wrapped(
                        #         Path("images/"),
                        #         filename,
                        #         track,
                        #         side
                        #     )
                        # )
                        # self.pending_tasks.add(task)
                    if message.startswith('OK : Done...'):
                        break
                # Wait for any remaining image saving tasks before continuing
                if self.pending_tasks:
                    bar.write("Waiting for remaining image saves to complete...")
                    await asyncio.gather(*self.pending_tasks)
                bar.close()
                bar_outer.update(1)
            except KeyboardInterrupt:
                await self.send_ws('stop')
                raise
            last_floppy_name = floppy_name
        
        bar_outer.close()

        print("Done dumping floppies")
        
        await asyncio.gather(
            self.return_heads(drives=list(range(len(floppy_names)))),
            self.upload_to_nas()
        )

        await self.send_ws("sound 2550 200")
        time.sleep(0.1)
        await self.send_ws("sound 2550 400")

        print("Finished completely")

@click.command()
@click.argument('address')
@click.argument('floppy_names', nargs=-1, required=True)
@click.option('--operator', default=None, help='Operator name (defaults to current system user)')
def main(address: str, floppy_names: tuple[str, ...], operator: str | None):
    """
    Dump floppy disks using Pauline.
    
    ADDRESS: The IP address or hostname of the Pauline device
    
    Names of the floppies to dump (one or more). Use '-' to skip a drive, '+' to increment last name, 'clean' for cleaning disk.
    """
    pauline = Pauline(address=address)
    asyncio.run(pauline.run_batch(floppy_names=list(floppy_names), operator=operator))

if __name__ == "__main__":
    main()

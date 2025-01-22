#!/usr/bin/env python

from sys import argv
import asyncio
from dataclasses import dataclass
import time
import datetime
import re
import tqdm
import asyncssh

import websockets
from config import FLOPPY_DRIVE_NAMES, OPERATOR_NAME

NUM_TRACKS = 82
#DUMP_TIME = 440
DUMP_TIME = 800
#DUMP_TIME = 800*2

INVENTORY_CODE="hh"

@dataclass
class Pauline():
    address: str

    async def connect(self):
        print("Connecting to websocket...")
        self.ws = await websockets.connect(f"ws://{self.address}:8080")

        print("Connecting to ssh...")
        self.ssh = await asyncssh.connect(self.address, username="pauline", password="pauline")

        result = await self.ssh.run("uname -s", check=True)
        assert result.stdout
        assert result.stdout.strip() == "Linux"

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

        result = await self.ssh.run("scp -P 7722 -r /home/pauline/Disks_Captures dumper@nas.herniarchiv.cz:dumps/pauline2/")

        print(result)
        print("Done uploading")

        await self.ssh.run("mkdir -p /home/pauline/Disks_Captures_Done")
        await self.ssh.run("mv /home/pauline/Disks_Captures/* /home/pauline/Disks_Captures_Done")

        print("Moved done disks")

    async def run_batch(self, floppy_names: list[str]):
        await self.connect()

        bar_outer = tqdm.tqdm(total=len(floppy_names), desc='floppy')
        bar_outer.update(0)
        last_floppy_name = None
        for floppy_index, (floppy_name, drive_name) in enumerate(zip(floppy_names, FLOPPY_DRIVE_NAMES)):
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
            filename = f"{datetime_str}_{OPERATOR_NAME}_{floppy_name}_{drive_name}"
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
                        #track = int(match.group(1))
                        #side = int(match.group(2))
                        #assert side < 2
                        #progress = track + 0.5 * side
                        bar.update(0.5)
                    if message.startswith('OK : Done...'):
                        break
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

if __name__ == "__main__":
    pauline = Pauline(address=argv[1])
    asyncio.run(pauline.run_batch(floppy_names=argv[2:]))

#!/usr/bin/env python

import asyncio
import time
import datetime
import re
import tqdm
from config import FLOPPY_DRIVE_NAMES, OPERATOR_NAME

from sys import argv

import websockets

NUM_TRACKS = 82


async def send_ws(ws, msg: str) -> None:
    await ws.send(msg)
    print(f">>> {msg}")

async def pauline_batch(pauline_addr: str, floppy_names: list[str]):
    async with websockets.connect(f"ws://{pauline_addr}:8080") as ws:
        bar_outer = tqdm.tqdm(total=len(floppy_names), desc='floppy')
        bar_outer.update(0)
        for floppy_index, (floppy_name, drive_name) in enumerate(zip(floppy_names, FLOPPY_DRIVE_NAMES)):
            num_str = f"{floppy_index + 1}/{len(floppy_names)}"
            datetime_str = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            if not floppy_name.startswith('rh'):
                floppy_name = f"rh{floppy_name}"
            filename = f"{datetime_str}_{OPERATOR_NAME}_{floppy_name}_{drive_name}"
            bar_outer.write(f"Dumping {floppy_name} ({num_str}): {filename}")
            await send_ws(ws, "set MACINTOSH_GCR_MODE 0")
            await send_ws(ws, "index_to_dump 0")
            await send_ws(ws, "dump_time 800")
            try:
                await send_ws(ws, f'dump {floppy_index} 0 {NUM_TRACKS} 0 1 0 0 0 0 "{filename}" "" 1 AUTO_INDEX_NAME "" "" ""')
                bar = tqdm.tqdm(total=NUM_TRACKS, desc='track', leave=False)
                bar.update(0)
                while True:
                    message = await ws.recv()
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
                await send_ws(ws, 'stop')
                raise
        
        bar_outer.close()
        print("Returning heads...")
        for floppy_index in range(len(floppy_names)):
            await send_ws(ws, f"recalibrate {floppy_index}")
            time.sleep(4)
    print("Done")
    # TODO read amount of space on SD card

if __name__ == "__main__":
    asyncio.run(pauline_batch(pauline_addr=argv[1], floppy_names=argv[2:]))

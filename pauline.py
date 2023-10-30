#!/usr/bin/env python

import asyncio
import time
import datetime
import re
import tqdm

from sys import argv

import websockets

NUM_TRACKS = 80
pauline_addr = "10.0.99.200"

async def send_ws(ws, msg: str) -> None:
    await ws.send(msg)
    print(f">>> {msg}")

async def pauline_batch(floppy_names):
    today = datetime.date.today().isoformat().replace('-', '')
    async with websockets.connect(f"ws://{pauline_addr}:8080") as ws:
        for floppy_index, floppy_name in enumerate(floppy_names):
            num_str = f"{floppy_index + 1}/{len(floppy_names)}"
            print(f"Dumping {floppy_name} ({num_str})")
            await send_ws(ws, "set MACINTOSH_GCR_MODE 0")
            await send_ws(ws, "index_to_dump 0")
            await send_ws(ws, "dump_time 800")
            await send_ws(ws, f'dump {floppy_index} 0 80 0 1 0 0 0 0 "{today}_{floppy_name}" "" 1 AUTO_INDEX_NAME "" "" ""')
            bar = tqdm.tqdm(total=NUM_TRACKS)
            bar.update(0)
            while True:
                message = await ws.recv()
                bar.write(f"[{num_str}] <<< {message.strip()}")
                # use regex to exttract 37 and 0 from ...t_rh6791-0001/track37.0.hxcstream
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
        
        print("Returning heads...")
        for floppy_index in range(len(floppy_names)):
            await send_ws(ws, f"recalibrate {floppy_index}")
            time.sleep(4)

    print("Done")
    # TODO read amount of space on SD card

if __name__ == "__main__":
    asyncio.run(pauline_batch(argv[1:]))

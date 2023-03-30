from __future__ import annotations
from typing import *

import asyncio
import sys
import contextlib
import aiofiles.threadpool

from chat_streams import split_lines, handle_writes


async def handle_reads(reader: asyncio.StreamReader) -> None:
    async for message in split_lines(reader):
        text = message.decode()
        print(f"Received {text!r}")
        if text == "quit":
            break


async def stream_file_to_queue(file: IO[str], queue: asyncio.Queue[bytes]) -> None:
    loop = asyncio.get_event_loop()
    async for message in aiofiles.threadpool.wrap(file, loop=loop):
        await queue.put(message.encode())


async def send_file(file: IO[str]) -> None:
    write_queue: asyncio.Queue[bytes] = asyncio.Queue()
    reader, writer = await asyncio.open_connection("127.0.0.1", 8888)
    read_handler = asyncio.create_task(handle_reads(reader))
    write_handler = asyncio.create_task(handle_writes(writer, write_queue))
    copy_handler = asyncio.create_task(stream_file_to_queue(file, write_queue))
    done, pending = await asyncio.wait(
        [read_handler, write_handler, copy_handler], return_when=asyncio.FIRST_COMPLETED
    )
    print("Closing the connection")
    for task in pending:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    writer.close()

if __name__ == "__main__":
    asyncio.run(send_file(sys.stdin))

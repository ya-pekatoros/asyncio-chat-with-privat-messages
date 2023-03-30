from __future__ import annotations
from typing import *

import asyncio
import contextlib

from chat_streams import split_lines, handle_writes


users: Dict[str, asyncio.Queue[bytes]] = {}


async def handle_commands(
    reader: asyncio.StreamReader, queue: asyncio.Queue[bytes], ctx: Dict[str, str]
) -> None:
    addr = ctx["addr"]
    my_nick = ctx["my_nick"]
    await queue.put(b"Welcome! Please, introduce yourself.")
    async for message in split_lines(reader):
        text = message.decode()
        print(f"Received {text!r} from {addr!r}")
        if text == "quit":
            await queue.put(message)
            break
        if text.startswith("I'm "):
            command, my_nick = text.split(" ", 1)
            users[my_nick] = queue
            ctx["my_nick"] = my_nick
        elif text.startswith("@"):
            if not my_nick:
                await queue.put(b"Please, introduce yourself.")
                continue
            at_nick, user_message = text.split(" ", 1)
            nick = at_nick[1:]
            if nick not in users:
                await queue.put(b"Unknown user: " + nick.encode())
                continue
            user_message = f"<{my_nick}> {user_message}"
            await users[nick].put(user_message.encode())


async def handle_connection(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    queue: asyncio.Queue[bytes] = asyncio.Queue()
    write_handler = asyncio.create_task(handle_writes(writer, queue))
    ctx = {
        "addr": str(writer.get_extra_info("peername")),
        "my_nick": "",
    }
    try:
        await handle_commands(reader, queue, ctx)
    finally:
        my_nick = ctx["my_nick"]
        if my_nick in users:
            del users[my_nick]
        print("Closing the connection")
        await queue.put(b"")
        with contextlib.suppress(asyncio.CancelledError):
            await write_handler
    writer.close()

async def main() -> None:
    server = await asyncio.start_server(handle_connection, "127.0.0.1", 8888)
    addr = server.sockets[0].getsockname() if server.sockets else "unknown"
    print(f"Serving on {addr}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())

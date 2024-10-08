# SPDX-License-Identifier:  CC-BY-SA-4.0

import sys
import random
import asyncio
import psutil
import random
from secrets import token_bytes
import math

import uvicorn


async def app(scope, receive, send, mean=0.02, std=0.001):
    """
    Echo the request body back in an HTTP response.
    """

    body = b""
    more_body = True
    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)
    """Redirect body to the actual HTTP server"""

    delay = random.gauss(mean, std)
    delay = min(delay, 10.0)
    await asyncio.sleep(delay)

    """Imitate a time consuming process by delay."""
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"text/plain"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": body,
        }
    )


async def main(app_, host, port, canceller, server_ref, concurrent_requesters):
    random.seed(token_bytes(16))

    workers = 1
    print("Starting Uvicorn with", workers, "workers.")

    asyncio.create_task(canceller())
    config = uvicorn.Config(
        app_,
        host=host,
        port=port,
        log_level="critical",
        workers=workers,
        http="h11",
    )
    server_ref[0] = uvicorn.Server(config)
    """Let parent process know this process started."""
    await server_ref[0].serve()


def server_main(args):
    uvicorn_server = [None]

    async def canceller():
        nonlocal uvicorn_server
        try:
            ab_proc = psutil.Process(args["AB_PID"])
            while ab_proc.is_running() and ab_proc.status() != psutil.STATUS_ZOMBIE:
                await asyncio.sleep(1)
        except psutil.NoSuchProcess:
            pass
        await asyncio.sleep(3)
        if uvicorn_server[0] is not None:
            await uvicorn_server[0].shutdown()
        for task in asyncio.all_tasks():
            task.cancel()

    """Automatically terminate after ab ends"""

    try:
        asyncio.run(
            main(
                app,
                args["HOST"],
                args["PORT"],
                canceller,
                uvicorn_server,
                args["CONCURRENT_REQUESTS"],
            )
        )
    except asyncio.exceptions.CancelledError:
        pass

    return 0


if __name__ == "__main__":
    args = {
        "HOST": "127.0.0.1",
        "PORT": 5000,
        "AB_PID": int(sys.argv[1]),
        "CONCURRENT_REQUESTS": int(sys.argv[2]),
    }

    server_main(args)

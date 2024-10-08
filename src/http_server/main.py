# SPDX-License-Identifier:  CC-BY-SA-4.0

import sys
import asyncio
import time
import getopt
import json
import random
from secrets import token_bytes
import math

import soyutnet
from soyutnet import SoyutNet
from soyutnet.constants import GENERIC_ID, GENERIC_LABEL, INVALID_ID

import uvicorn
import psutil

from . import uvicorn_main


def USAGE():
    """
    .. _usage_http_server:

    **Arguments:**

      -T <time (sec)>
        total simulation time in seconds (:math:`T`)

        Default: 10
      -o <filename>
        output file name to write results. If empty, prints to stdout.
      -p <rate (Hz)>
        new token output rate of the producer at each second

        Default: 10
      -H hostname

        Default: 127.0.0.1
      -P port

        Default: 5000
      -G
        if provided, the script generates PT net graph and exits

      -A ab command's PID

      -C number of concurrent requests expected

    **Example**
      python src/http_balancer/main.py -p 100
    """
    print(USAGE.__doc__)


def main(argv):
    """
    Main entry point of the simulation.

    :param argv: Command line arguments
    :return: Exit status
    """
    random.seed(token_bytes(16))

    OUTPUT_FILENAME = None
    OUTPUT_FILE = sys.stdout
    GENERATE_GRAPH_AND_EXIT = False
    HOST = "127.0.0.1"
    PORT = 5000
    AB_PID = None
    CONCURRENT_REQUESTS = 4
    CONTROLLER_TYPE = "SN"
    BRANCH_COUNT = 1

    opts, args = getopt.getopt(argv[1:], "r:o:GH:P:A:C:c:")

    for o, a in opts:
        if o == "-r":
            tmp = a.split(",")
            tmp[1:] = [float(val) for val in tmp[1:]]
            RNG_PARAMS = tuple(tmp)
        elif o == "-o":
            OUTPUT_FILENAME = a
            OUTPUT_FILE = open(a, "a")
        elif o == "-G":
            GENERATE_GRAPH_AND_EXIT = True
        elif o == "-H":
            HOST = a
        elif o == "-P":
            PORT = int(a)
        elif o == "-A":
            AB_PID = int(a)
        elif o == "-C":
            CONCURRENT_REQUESTS = int(a)
        elif o == "-c":
            CONTROLLER_TYPE = a

    net = SoyutNet()

    treg = net.TokenRegistry()
    req_queues = [asyncio.Queue() for i in range(CONCURRENT_REQUESTS)]

    LABEL_MAX = CONCURRENT_REQUESTS

    label_counter = 0

    def new_label():
        nonlocal label_counter
        label_counter %= LABEL_MAX
        label_counter += 1
        """Assign a label from 1 to LABEL_MAX to determine the path it will follow in the net."""
        return label_counter

    def new_http_request_token(scope, receive, send, cond):
        label = new_label()
        token = net.Token(label=label, binding=(scope, receive, send, cond))
        treg.register(token)

        return (token._label, token._id)

    async def uvicorn_app(scope, receive, send):
        if scope["type"] != "http":
            return
        cond = asyncio.Semaphore(value=0)
        token = new_http_request_token(scope, receive, send, cond)
        label = token[0]
        req_queues[(label - 1) // BRANCH_COUNT].put_nowait(token)
        await cond.acquire()
        """Wait until endpoint fullfills HTTP request"""

    async def producer(place):
        index = int(place._name[3:])
        token = await req_queues[index].get()
        return [token]

    """Inject token"""

    consumer_stats = {}

    async def consumer(place):
        async def http_server(uvicorn_scope, uvicorn_receive, uvicorn_send):
            await uvicorn_main.app(uvicorn_scope, uvicorn_receive, uvicorn_send)

        nonlocal consumer_stats
        t0 = time.time()
        ident = place.ident()
        if ident not in consumer_stats:
            """Initialize stats at first call of the producer."""
            consumer_stats[ident] = {"started_at": time.time(), "count": 0}
            """Store initial time and number of requests processed to calculate requests per second."""

        label = place._input_arcs[0]._labels[0]
        token = place.get_token(label)
        T = time.time()
        if not token:
            consumer_stats[ident]["last_at"] = time.time()
            return

        actual_token = treg.pop_entry(*token)
        """Get actual SoyutNet.Token object from SoyutNet.TokenRegistry"""
        if actual_token is None:
            consumer_stats[ident]["last_at"] = time.time()
            return

        uvicorn_scope, uvicorn_receive, uvicorn_send, cond = actual_token.get_binding()
        """Get object binded to the actual token"""
        await http_server(uvicorn_scope, uvicorn_receive, uvicorn_send)
        """Fulfill the request."""
        cond.release()
        """Inform uvicorn_app that request is replied"""

        consumer_stats[ident]["count"] += 1
        consumer_stats[ident]["last_at"] = time.time()

    reg = net.PTRegistry()
    label_counter = 0
    for i in range(CONCURRENT_REQUESTS):
        proi = net.SpecialPlace(f"pro{i}", producer=producer)
        reg.register(proi)
        for j in range(BRANCH_COUNT):
            label_counter += 1
            tij = net.Transition(f"t{i}_{j}")
            conij = net.SpecialPlace(f"con{i}_{j}", consumer=consumer)
            reg.register(tij)
            reg.register(conij)
            proi.connect(tij, labels=[label_counter])
            tij.connect(conij, labels=[label_counter])

    LABEL_MAX = label_counter
    label_counter = 0

    if GENERATE_GRAPH_AND_EXIT:
        OUTPUT_FILE.close()
        with open(OUTPUT_FILENAME, "w") as fh:
            fh.write(reg.generate_graph())

        return 0

    uvicorn_server = [None]

    async def canceller():
        try:
            ab_proc = psutil.Process(AB_PID)
            while ab_proc.is_running() and ab_proc.status() != psutil.STATUS_ZOMBIE:
                await asyncio.sleep(1)
        except psutil.NoSuchProcess:
            pass
        await asyncio.sleep(1)
        if uvicorn_server[0] is not None:
            await uvicorn_server[0].shutdown()
        soyutnet.terminate()

    """Automatically terminate after ab ends"""

    soyutnet.run(
        reg,
        extra_routines=[
            uvicorn_main.main(
                uvicorn_app, HOST, PORT, canceller, uvicorn_server, CONCURRENT_REQUESTS
            )
        ],
    )
    """Start simulation"""

    for name in consumer_stats:
        stats = consumer_stats[name]
        count = stats["count"]
        if count > 0:
            stats["req_per_sec"] = stats["count"] / (
                stats["last_at"] - stats["started_at"]
            )
        else:
            stats["req_per_sec"] = 0

    print(
        json.dumps(
            {
                "params": {
                    "produce_rate": CONCURRENT_REQUESTS,
                },
                "stats": consumer_stats,
            }
        ),
        file=OUTPUT_FILE,
    )
    OUTPUT_FILE.close()
    """Dump results"""

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

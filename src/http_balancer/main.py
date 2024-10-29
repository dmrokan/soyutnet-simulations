# SPDX-License-Identifier:  CC-BY-SA-4.0

import sys
import asyncio
from multiprocessing import Process, Semaphore
import time
import getopt
import json

import soyutnet
from soyutnet import SoyutNet
from soyutnet.constants import GENERIC_ID, GENERIC_LABEL

import uvicorn
import psutil

from ..common import logged


def server_main(args, cond):
    import random
    from secrets import token_bytes

    random.seed(token_bytes(16))

    RNG_PARAMS = list(args["RNG_PARAMS"])

    def normal_rng(*args):
        return random.gauss(*args)

    def exponential_rng(*args):
        return random.expovariate(1.0 / args[0])

    print(f"Process {args['ID']} started")

    _rand = None
    match RNG_PARAMS[0]:
        case "normal":
            _rand = normal_rng
        case _:
            _rand = exponential_rng

    start_time = None
    total_time = args["RUNTIME"]
    load_vs_time = args["LOAD"]

    def rand():
        nonlocal start_time
        nonlocal RNG_PARAMS
        if start_time is None:
            start_time = time.time()

        def adjust_load():
            delta_time = (time.time() - start_time) / total_time
            for l in load_vs_time:
                if l[0] >= delta_time:
                    RNG_PARAMS[1] = l[1] * args["RNG_PARAMS"][1]
                    break

        adjust_load()
        return _rand(*(RNG_PARAMS[1:]))

    # [[http-server-defs-start]]

    async def read_body(receive):
        """
        Read and return the entire body from an incoming ASGI message.
        """
        body = b""
        more_body = True

        while more_body:
            message = await receive()
            body += message.get("body", b"")
            more_body = message.get("more_body", False)

        return body

    async def uvicorn_app(scope, receive, send):
        """
        Echo the request body back in an HTTP response.
        """
        body = await read_body(receive)
        delay_amount = rand()
        await asyncio.sleep(delay_amount)
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

    # [[http-server-defs-end]]

    uvicorn_server = None

    async def canceller():
        nonlocal uvicorn_server
        if args["AB_PID"] is None:
            await asyncio.sleep(args["RUNTIME"])
        else:
            try:
                ab_proc = psutil.Process(args["AB_PID"])
                while ab_proc.is_running() and ab_proc.status() != psutil.STATUS_ZOMBIE:
                    await asyncio.sleep(1)
            except psutil.NoSuchProcess:
                pass
            await asyncio.sleep(3)
        if uvicorn_server is not None:
            await uvicorn_server.shutdown()
        for task in asyncio.all_tasks():
            task.cancel()

    async def uvicorn_main():
        nonlocal uvicorn_server
        asyncio.create_task(canceller())
        config = uvicorn.Config(
            uvicorn_app,
            host=args["HOST"],
            port=args["PORT"],
            log_level="critical",
            http="h11",
        )
        uvicorn_server = uvicorn.Server(config)
        cond.release()
        """Let parent process know this process started."""
        await uvicorn_server.serve()

    try:
        asyncio.run(uvicorn_main())
    except asyncio.exceptions.CancelledError:
        pass

    print(f"Process {args['ID']} ends")
    return 0


def USAGE():
    """
    .. _usage_http_balancer:

    **Arguments:**

      -T <time (sec)>
        total simulation time in seconds (:math:`T`)

        Default: 10
      -c <none|C1|C2|C3>
        :ref:`controller <controllers>` type

        Default: C1
      -o <filename>
        output file name to write results. If empty, prints to stdout.
      -L <option>
        change in server load by time
          e.g. 0.2,2;0.8,0.33;

          Means load on 2nd consumer will be two times more than 1st consumer
          after time instant :math:`0.2T` until time instant :math:`0.8T`. Then,
          its load will be 1/3 of 1st consumer's load until the end of simulation.

        Default: "0,1;"
      -p <rate (Hz)>
        new token output rate of the producer at each second

        Default: 10
      -H hostname
        Default: 127.0.0.1
      -P ports
        port1,port2

        Default: 8888,8889
      -r <option>
        random number generator params
          e.g. exponential,0.1

          Meaning consumation time of a token takes a random amount of time
          with an exponential distrbution having an average of 0.1 seconds.

        Default: exponential,0.5
      -G
        if provided, the script generates PT net graph and exits
      -K
        comman separated PI controller gain values
          e.g. 1e-1,1e-2

        Default: 1e-2,1e-4

      -A ab command's PID

      -C number of concurrent requests expected

    **Example**

      python src/http_balancer/main.py -T 8.5 -r exponential,0.05 -p 100 -c none
    """
    print(USAGE.__doc__)


@logged
def main(argv, OUTPUT_FILE):
    """
    Main entry point of the simulation.

    :param argv: Command line arguments
    :return: Exit status
    """

    RNG_PARAMS = ("exponential", 1 / 2)
    CONTROLLER_ENABLED = True
    PROC_COUNT = 2
    STOP_AFTER = 10
    L = 2
    OUTPUT_FILENAME = None
    LOAD = []
    CONTROLLER_TYPE = "C1"
    GENERATE_GRAPH_AND_EXIT = False
    HOST = "127.0.0.1"
    PORTS = [8888, 8889]
    PROXY_HOST = "127.0.0.1"
    PROXY_PORT = 5000
    K_PI = []
    AB_PID = None
    CONCURRENT_REQUESTS = None

    opts, args = getopt.getopt(argv[1:], "r:c:T:o:l:p:GH:P:K:X:A:C:L:")

    for o, a in opts:
        if o == "-r":
            tmp = a.split(",")
            tmp[1:] = [float(val) for val in tmp[1:]]
            RNG_PARAMS = tuple(tmp)
        elif o == "-c":
            CONTROLLER_TYPE = a
        elif o == "-T":
            STOP_AFTER = float(a)
        elif o == "-o":
            OUTPUT_FILENAME = a
        elif o == "-L":
            load_vs_time = a.split(";")
            for l in load_vs_time:
                if l:
                    LOAD.append(tuple([float(val) for val in l.split(",")]))
        elif o == "-G":
            GENERATE_GRAPH_AND_EXIT = True
        elif o == "-H":
            HOST = a
        elif o == "-P":
            PORTS = [int(val) for val in a.split(",")]
        elif o == "-K":
            K_PI = [float(val) for val in a.split(",")]
            if len(K_PI) != 2:
                raise RuntimeError(f"Option -K is invalid '{a}'")
        elif o == "-X":
            PROXY_HOST, PROXY_PORT = a.split(",")
            PROXY_PORT = int(PROXY_PORT)
        elif o == "-A":
            AB_PID = int(a)
        elif o == "-C":
            CONCURRENT_REQUESTS = int(a)

    if CONTROLLER_TYPE == "none":
        CONTROLLER_ENABLED = False

    SERVER_RUNTIME = STOP_AFTER + 1
    """Server should run longer than clients."""

    net = SoyutNet()
    net.SLOW_MOTION = True
    net.LOOP_DELAY = 0

    # [[token-gen-defs-start]]

    treg = net.TokenRegistry()
    req_queue = asyncio.Queue()

    def new_http_request_token(scope, receive, send, cond):
        token = net.Token(label=L, binding=(scope, receive, send, cond))
        treg.register(token)

        return (token._label, token._id)

    async def uvicorn_app(scope, receive, send):
        if scope["type"] != "http":
            return
        cond = asyncio.Condition()
        token = new_http_request_token(scope, receive, send, cond)
        await req_queue.put(token)
        async with cond:
            await cond.wait()
        """Wait until endpoint fullfills HTTP request"""

    # [[token-gen-defs-end]]

    uvicorn_server = None

    async def uvicorn_main():
        nonlocal uvicorn_server
        config = uvicorn.Config(
            uvicorn_app,
            host=PROXY_HOST,
            port=PROXY_PORT,
            log_level="critical",
            http="h11",
        )
        uvicorn_server = uvicorn.Server(config)
        await uvicorn_server.serve()

    # [[producer-defs-start]]

    async def producer(place):
        token = await req_queue.get()
        return [token]

    """Inject token"""

    # [[producer-defs-end]]

    sensors = [asyncio.Queue() for i in range(PROC_COUNT)]
    consumer_stats = {}

    async def consumer(place):
        async def http_proxy(uvicorn_scope, uvicorn_receive, uvicorn_send):
            http_data = uvicorn_scope.get("method", "").encode("ascii") + b" "
            http_data += uvicorn_scope.get("raw_path", b"/") + b"?"
            http_data += uvicorn_scope.get("query_string", b"") + b" "
            http_data += (
                b"HTTP/"
                + uvicorn_scope.get("http_version", "1.0").encode("ascii")
                + b"\r\n"
            )
            for h in uvicorn_scope.get("headers", []):
                http_data += b": ".join(h) + b"\r\n"
            http_data += b"\r\n"

            reader, writer = await asyncio.open_connection(HOST, PORTS[index])
            writer.write(http_data)
            await writer.drain()
            """Redirect header to the actual HTTP server"""

            more_body = True
            while more_body:
                message = await uvicorn_receive()
                body = message.get("body", b"")
                writer.write(body)
                await writer.drain()
                more_body = message.get("more_body", False)
            """Redirect body to the actual HTTP server"""

            header = await reader.readuntil(b"\r\n" * 2)
            to_find = b"\r\ncontent-length: "
            str_start = header.rfind(to_find) + len(to_find)
            header = header[str_start:]
            str_end = header.find(b"\r\n")
            content_length = int(header[:str_end])
            data = await reader.read(content_length)
            """Read response from the actual HTTP server."""
            writer.close()
            await writer.wait_closed()
            """Close connection to the actual HTTP server"""
            await uvicorn_send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        (b"content-type", b"text/plain"),
                        (b"content-length", str(len(data)).encode()),
                    ],
                }
            )
            await uvicorn_send(
                {
                    "type": "http.response.body",
                    "body": data,
                }
            )
            """Redirect response to the requester"""

        # [[actual-token-defs-start]]

        t0 = time.time()

        def dt():
            return time.time() - t0

        nonlocal consumer_stats
        t0 = time.time()
        ident = place.ident()
        index = int(place._name[1:]) - 1
        """Get branch index (0 or 1)"""
        sensor = sensors[index]
        if ident not in consumer_stats:
            """Initialize stats at first call of the producer."""
            consumer_stats[ident] = {"started_at": time.time(), "count": 0}
            """Store initial time and number of requests processed to calculate requests per second."""
            sensor.put_nowait((True, dt()))
            """Initial push to the controllers, otherwise they will stuck at waiting the sensor."""

        label = L
        token = place.get_token(label)
        T = time.time()
        if not token:
            consumer_stats[ident]["last_at"] = time.time()
            sensor.put_nowait((False, dt()))
            """If there is no new token in the buffer, inform the controller."""
            return

        actual_token = treg.pop_entry(*token)
        """Get actual SoyutNet.Token object from SoyutNet.TokenRegistry"""
        if actual_token is None:
            consumer_stats[ident]["last_at"] = time.time()
            sensor.put_nowait((False, dt()))
            """If there is no actual token in the register, inform the controller."""
            return

        # [[actual-token-defs-end]]

        # [[token-processing-defs-start]]

        uvicorn_scope, uvicorn_receive, uvicorn_send, cond = actual_token.get_binding()
        """Get object binded to the actual token"""
        await http_proxy(uvicorn_scope, uvicorn_receive, uvicorn_send)
        """Fulfill the request."""
        async with cond:
            cond.notify_all()
        """Inform uvicorn_app that request is replied"""

        # [[token-processing-defs-end]]

        sensor.put_nowait((True, dt()))
        """Inform the controller."""
        consumer_stats[ident]["count"] += 1
        consumer_stats[ident]["last_at"] = time.time()

    # [[controller-defs-start]]

    ci = [0.0, 0.0]
    """Integrator states"""
    Kp = 1e-2 if not K_PI else K_PI[0]
    """Propotional gain"""
    Ki = 1e-4 if not K_PI else K_PI[1]
    """Integrator gain"""
    Zi = 1e-2
    """Integrator damping"""
    count = [0, 0]
    """Total number of times the transitions t13 and t23 fire."""
    total_delay = [0.0, 0.0]
    """Total amount of time spent by consumers for completing HTTP requests."""

    async def controller(place):
        nonlocal ci
        if not CONTROLLER_ENABLED:
            """This happens when controller is chosen 'none'"""
            return True
        index = int(place._name[1:]) - 1
        """Get branch index."""
        sensor = sensors[index]
        value: tuple[bool, float] = await sensor.get()
        """Receive a notification from the consumer."""
        if CONTROLLER_TYPE == "C2":
            """This happens when controller is chosen 'C2'"""
            count[index] += 1
            err = count[index] - count[1 - index]
            """Calculate the difference between branches"""
            sleep_amount = Kp * err + ci[index]
            ci[index] = (1.0 - Zi) * ci[index] + Ki * err
            """PI controller"""
            if abs(sleep_amount) > 1e4:
                """This should never happen."""
                print("!!!", sleep_amount, "!!!")
                ci[index] = 0.0
            await net.sleep(sleep_amount)
            """Give a push to the other branch when it is slower."""
            return True
        elif CONTROLLER_TYPE == "C3":
            """This happens when controller is chosen 'C3'"""
            count[index] += 1
            total_delay[index] += value[1]

            # [[err-defs-start]]

            err = total_delay[index] - total_delay[1 - index]
            """Calculate the difference between branches"""
            err += 0.0 - total_delay[index]
            """Try to minimize the total time consumed."""

            # [[err-defs-end]]

            sleep_amount = 1e2 * Kp * err + ci[index]
            ci[index] = (1.0 - Zi) * ci[index] + 1e2 * Ki * err
            """PI controller"""
            if abs(sleep_amount) > 1e4:
                """This should never happen."""
                print("!!!", sleep_amount, "!!!")
                ci[index] = 0.0
            await net.sleep(sleep_amount)
            """Give a push to the other branch when it is slower."""
            return True

        return value[0]  # This is the case when controller is 'C1'.

    # [[controller-defs-end]]

    p0 = net.SpecialPlace("p0", producer=producer)
    t0 = net.Transition("t0")
    p1 = net.Place("p1")
    p11 = net.Place("p11")
    o12 = net.Observer(verbose=True)
    p12 = net.Place("p12", observer=o12)
    t11 = net.Transition("t11")
    t12 = net.Transition("t12")
    t13 = net.Transition("t13")
    e1 = net.SpecialPlace("e1", consumer=consumer)

    k1 = net.Place(
        "k1", initial_tokens={GENERIC_LABEL: [GENERIC_ID] * 1}, processor=controller
    )
    """Add initial tokens, otherwise PT nets will stuck at its initial state."""

    p21 = net.Place("p21")
    o22 = net.Observer(verbose=True)
    p22 = net.Place("p22", observer=o22)
    t21 = net.Transition("t21")
    t22 = net.Transition("t22")
    t23 = net.Transition("t23")
    e2 = net.SpecialPlace("e2", consumer=consumer)

    k2 = net.Place(
        "k2", initial_tokens={GENERIC_LABEL: [GENERIC_ID] * 1}, processor=controller
    )

    reg = net.PTRegistry()
    reg.register(p0)
    reg.register(t0)
    reg.register(p1)
    reg.register(p11)
    reg.register(p12)
    reg.register(t11)
    reg.register(t12)
    reg.register(t13)

    reg.register(e1)
    reg.register(k1)
    reg.register(p21)
    reg.register(p22)
    reg.register(t21)
    reg.register(t22)
    reg.register(t23)
    reg.register(e2)
    reg.register(k2)

    (
        p0.connect(t0, labels=[L])
        .connect(p1, labels=[L])
        .connect(t11, labels=[L])
        .connect(p11, weight=2, labels=[GENERIC_LABEL, L])
        .connect(t12, weight=2, labels=[GENERIC_LABEL, L])
        .connect(p12, labels=[L])
        .connect(t13, labels=[L])
        .connect(e1, labels=[L]),
        t12.connect(k1).connect(t11),
    )
    (
        p1.connect(t21, labels=[L])
        .connect(p21, weight=2, labels=[GENERIC_LABEL, L])
        .connect(t22, weight=2, labels=[GENERIC_LABEL, L])
        .connect(p22, labels=[L])
        .connect(t23, labels=[L])
        .connect(e2, labels=[L]),
        t22.connect(k2).connect(t21),
    )

    if GENERATE_GRAPH_AND_EXIT:
        OUTPUT_FILE.truncate(0)
        OUTPUT_FILE.write(reg.generate_graph(label_names={L: "◆", GENERIC_LABEL: "○"}))

        return 0

    loads = [[], []]
    for l in LOAD:
        loads[0].append((l[0], l[1]))
    """Assign a larger load to consumer 1"""

    procs = set()
    init_conditions = set()
    for i in range(PROC_COUNT):
        args = {
            "ID": i,
            "RUNTIME": SERVER_RUNTIME,
            "HOST": HOST,
            "PORT": PORTS[i],
            "RNG_PARAMS": RNG_PARAMS,
            "LOAD": loads[i],
            "AB_PID": AB_PID,
        }
        cond = Semaphore(value=0)
        proc = Process(
            target=server_main,
            args=(
                args,
                cond,
            ),
        )
        proc.start()
        procs.add(proc)
        init_conditions.add(cond)
    """Started TCP servers"""

    [cond.acquire() for cond in init_conditions]
    """Make sure TCP servers started"""

    async def canceller():
        nonlocal uvicorn_server
        if AB_PID is None:
            await asyncio.sleep(STOP_AFTER)
        else:
            try:
                ab_proc = psutil.Process(AB_PID)
                while ab_proc.is_running() and ab_proc.status() != psutil.STATUS_ZOMBIE:
                    await asyncio.sleep(1)
            except psutil.NoSuchProcess:
                pass
            await asyncio.sleep(1)
        if uvicorn_server is not None:
            await uvicorn_server.shutdown()
        soyutnet.terminate()

    """Automatically terminate after an amount of time"""

    # [[loop-start-defs-start]]

    soyutnet.run(reg, extra_routines=[canceller(), uvicorn_main()])
    """Start simulation"""

    # [[loop-start-defs-end]]

    for proc in procs:
        proc.join()

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
                    "rng": RNG_PARAMS,
                    "control": CONTROLLER_ENABLED,
                    "controller_type": CONTROLLER_TYPE,
                    "produce_rate": CONCURRENT_REQUESTS,
                },
                "stats": consumer_stats,
            }
        ),
        file=OUTPUT_FILE,
    )
    """Dump results"""

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

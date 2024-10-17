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

MESSAGE = b"EXCHANGED"
MESSAGE_SIZE = len(MESSAGE)


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

    async def canceller():
        await asyncio.sleep(args["RUNTIME"])
        for task in asyncio.all_tasks():
            task.cancel()

    # [[tcp-server-defs-start]]

    async def handle_echo(reader, writer):
        data = await reader.read(MESSAGE_SIZE)
        delay_amount = rand()
        await asyncio.sleep(delay_amount)
        """Imitate a time consuming process by delay."""
        writer.write(data)
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    # [[tcp-server-defs-end]]

    async def main():
        server = await asyncio.start_server(handle_echo, args["HOST"], args["PORT"])

        asyncio.create_task(canceller())

        addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
        print(f"Serving on {addrs}")
        async with server:
            cond.release()
            await server.serve_forever()

    try:
        asyncio.run(main())
    except asyncio.exceptions.CancelledError:
        pass

    print(f"Process {args['ID']} ends")
    return 0


def USAGE():
    """
    .. _usage_pi_controller:

    **Arguments:**

      -T <time (sec)>
        total simulation time in seconds (:math:`T`)

        Default: 10
      -c <none|C1|C2>
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

    **Example**

      python src/pi_controller/main.py -T 8.5 -r exponential,0.05 -p 100 -c none
    """
    print(USAGE.__doc__)


def main(argv):
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
    OUTPUT_FILE = sys.stdout
    LOAD = []
    CONTROLLER_TYPE = "C1"
    PRODUCE_RATE = 10
    GENERATE_GRAPH_AND_EXIT = False
    HOST = "127.0.0.1"
    PORTS = [8888, 8889]
    K_PI = []

    opts, args = getopt.getopt(argv[1:], "r:c:T:o:l:p:GH:P:K:")

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
            OUTPUT_FILE = open(a, "a")
        elif o == "-L":
            load_vs_time = a.split(";")
            for l in load_vs_time:
                LOAD.append(tuple([float(val) for val in l.split(",")]))
        elif o == "-p":
            PRODUCE_RATE = float(a)
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

    if CONTROLLER_TYPE == "none":
        CONTROLLER_ENABLED = False

    PRODUCE_DELAY = 1.0 / PRODUCE_RATE

    SERVER_RUNTIME = STOP_AFTER + 1
    """Server should run longer than clients."""

    # [[loop-delay-defs-start]]

    net = SoyutNet()
    net.SLOW_MOTION = True
    net.LOOP_DELAY = 0

    # [[loop-delay-defs-end]]

    # [[producer-defs-start]]

    token_id = 0

    async def producer(place):
        nonlocal token_id
        await net.sleep(PRODUCE_DELAY)
        token_id += 1
        return [(L, token_id)]

    # [[producer-defs-end]]

    # [[consumer-defs-start]]

    sensors = [asyncio.Queue() for i in range(PROC_COUNT)]
    consumer_stats = {}

    async def consumer(place):
        async def echo_client():
            """Simple TCP echo client"""
            reader, writer = await asyncio.open_connection(HOST, PORTS[index])
            writer.write(MESSAGE)
            await writer.drain()
            data = await reader.read(MESSAGE_SIZE)
            writer.close()
            await writer.wait_closed()

        nonlocal consumer_stats
        start_time = 0
        ident = place.ident()
        index = int(place._name[1:]) - 1
        """Get branch index (0 or 1)"""
        sensor = sensors[index]
        if ident not in consumer_stats:
            """Initialize stats at first call of the producer."""
            consumer_stats[ident] = {"started_at": time.time(), "count": 0}
            """Store initial time and number of requests processed to calculate requests per second."""
            sensor.put_nowait(1)
            """Initial push to the controllers, otherwise they will stuck at waiting the sensor."""

        label = L
        token = place.get_token(label)
        T = time.time()
        if not token:
            consumer_stats[ident]["last_at"] = time.time()
            sensor.put_nowait(0)
            """If there is no new token in the buffer, inform the controller."""
            return

        await echo_client()
        """Fullfill the request."""

        sensor.put_nowait(1)
        """Inform the controller."""
        consumer_stats[ident]["count"] += 1
        consumer_stats[ident]["last_at"] = time.time()

    # [[consumer-defs-end]]

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

    async def controller(place):
        nonlocal ci
        if not CONTROLLER_ENABLED:
            """This happens when controller is chosen 'none'"""
            return True
        index = int(place._name[1:]) - 1
        """Get branch index."""
        sensor = sensors[index]
        value = await sensor.get()
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

        return value > 0  # This is the case when controller is 'C1'.

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
        OUTPUT_FILE.close()
        with open(OUTPUT_FILENAME, "w") as fh:
            fh.write(reg.generate_graph(label_names={L: "◆", GENERIC_LABEL: "○"}))

        return 0

    loads = [[], []]
    for l in LOAD:
        loads[1].append((l[0], l[1]))
    """Assign a larger load to consumer 2"""

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

    async def scheduled():
        await asyncio.sleep(STOP_AFTER)
        soyutnet.terminate()

    """Automatically terminate after an amount of time"""

    soyutnet.run(reg, extra_routines=[scheduled()])
    """Start simulation"""

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
                    "produce_rate": PRODUCE_RATE,
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

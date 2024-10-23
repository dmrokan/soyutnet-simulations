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


def USAGE():
    """
    .. _usage_timed_net:

    **Arguments:**
      -r <rng params>
        mu1,std1,mu2,std2 (units are seconds)

        Default: 300,60,600,180
      -T <time (sec)>
        total simulation time in seconds

        Default: 2
      -o <filename>
        output file name to write results. If empty, prints to stdout.
      -G
        if provided, the script generates PT net graph and exits

    **Example**
      python src/timed_net/main.py -r 100,10,200,25 -T 2
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
    SIMULATION_TIME = 2

    MINS = 60

    PRODUCER1_DELAY = (5 * MINS, 1 * MINS)
    PRODUCER2_DELAY = (10 * MINS, 3 * MINS)
    PRODUCER1_LABEL = 1
    PRODUCER2_LABEL = 2
    T0 = 0

    opts, args = getopt.getopt(argv[1:], "r:o:GH:P:A:C:c:")

    for o, a in opts:
        if o == "-r":
            tmp = a.split(",")
            PRODUCER1_DELAY = tuple(float(val) * MINS for val in tmp[:2])
            PRODUCER2_DELAY = tuple(float(val) * MINS for val in tmp[2:])
        elif o == "-o":
            OUTPUT_FILENAME = a
            OUTPUT_FILE = open(a, "a")
        elif o == "-G":
            GENERATE_GRAPH_AND_EXIT = True
        elif o == "-T":
            SIMULATION_TIME = float(a)

    net = SoyutNet()

    # [[timed-tr-defs-start]]

    class TimedTransition(soyutnet.Transition):
        def __init__(self, name, rng_params, *args, **kwargs):
            super().__init__(name=name, net=net, *args, **kwargs)
            self._rng_params = rng_params

        def _delay(self):
            return round(random.gauss(*self._rng_params))

        async def _process_tokens(self):
            for label in self._tokens:
                ids = self._tokens[label]
                self._tokens[label] = list(map(lambda x: x + self._delay(), ids))
                """Add producer delay"""

            return await super()._process_tokens()

    # [[timed-tr-defs-end]]

    # [[combiner-tr-defs-starts]]

    class CombinerTransition(soyutnet.Transition):
        def __init__(self, *args, **kwargs):
            super().__init__(net=net, *args, **kwargs)

        async def _process_tokens(self):
            max_id = 0
            for label in self._tokens:
                ids = self._tokens[label]
                if ids:
                    max_id = max(max_id, max(ids))
            for label in self._tokens:
                self._tokens[label] = [max_id] * len(self._tokens[label])
                """Total delay is the max of two branches"""

            return await super()._process_tokens()

    # [[combiner-tr-defs-ends]]

    # [[stock-counter-defs-starts]]

    production_time = [0]

    async def stock_counter(tr):
        nonlocal production_time
        t = None
        for label in tr._tokens:
            ids = tr._tokens[label]
            if not ids:
                continue
            for id in ids:
                if t is None:
                    t = id
                    production_time.append(t)
                else:
                    assert t == id

        return True

    # [[stock-counter-defs-ends]]

    reg = net.PTRegistry()

    p3 = net.Place("p3")

    p1 = net.Place("p1", initial_tokens={PRODUCER1_LABEL: [T0] * 1})
    t11 = TimedTransition("t11", PRODUCER1_DELAY)
    t12 = net.Transition("t12")
    q1 = net.Place("q1")
    (
        p1.connect(t11, labels=[PRODUCER1_LABEL], weight=1)
        .connect(q1, labels=[PRODUCER1_LABEL], weight=1)
        .connect(t12, labels=[PRODUCER1_LABEL], weight=1)
        .connect(p3, labels=[PRODUCER1_LABEL], weight=1)
    )

    p2 = net.Place("p2", initial_tokens={PRODUCER2_LABEL: [T0] * 1})
    t21 = TimedTransition("t21", PRODUCER2_DELAY)
    t22 = net.Transition("t22")
    q2 = net.Place("q2")
    (
        p2.connect(t21, labels=[PRODUCER2_LABEL], weight=1)
        .connect(q2, labels=[PRODUCER2_LABEL], weight=1)
        .connect(t22, labels=[PRODUCER2_LABEL], weight=1)
        .connect(p3, labels=[PRODUCER2_LABEL], weight=1)
    )

    stock_observer = net.Observer(verbose=True)
    t31 = CombinerTransition("t31")
    t32 = net.Transition("t32", processor=stock_counter)
    q3 = net.Place("q3", observer=stock_observer)
    (
        p3.connect(t31, labels=[PRODUCER2_LABEL, PRODUCER1_LABEL], weight=2)
        .connect(q3, labels=[PRODUCER2_LABEL, PRODUCER1_LABEL], weight=2)
        .connect(t32, labels=[PRODUCER2_LABEL, PRODUCER1_LABEL], weight=2)
    )

    t32.connect(p1, labels=[PRODUCER1_LABEL], weight=1)
    t32.connect(p2, labels=[PRODUCER2_LABEL], weight=1)

    {
        reg.register(pt)
        for pt in [
            p1,
            q1,
            t11,
            t12,
            p2,
            q2,
            t21,
            t22,
            p3,
            q3,
            t31,
            t32,
        ]
    }

    if GENERATE_GRAPH_AND_EXIT:
        OUTPUT_FILE.close()
        with open(OUTPUT_FILENAME, "w") as fh:
            fh.write(reg.generate_graph())

        return 0

    # [[loop-start-defs-start]]

    async def canceller():
        await net.sleep(SIMULATION_TIME)
        soyutnet.terminate()

    soyutnet.run(reg, extra_routines=[canceller()])
    """Start simulation"""

    # [[loop-start-defs-end]]

    OUTPUT_FILE.write(
        json.dumps(
            {
                "params": {
                    "PRODUCER1_DELAY": PRODUCER1_DELAY,
                    "PRODUCER2_DELAY": PRODUCER2_DELAY,
                },
                "production_time": production_time,
            }
        )
    )

    OUTPUT_FILE.close()
    """Dump results"""

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

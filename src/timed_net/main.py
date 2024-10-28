# SPDX-License-Identifier:  CC-BY-SA-4.0

import sys
import asyncio
import time
import getopt
import json
import random
from secrets import token_bytes
import math
from collections import UserList, OrderedDict
import operator
from functools import reduce
from enum import Enum, auto

import soyutnet
from soyutnet import SoyutNet
from soyutnet.constants import GENERIC_ID, GENERIC_LABEL, INVALID_ID

from . import results


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

      -W
        if provided, uses a weak comparion metric for convergence which
        highly increase simulation speed with the cost of degraded accuracy.

      -C <strict|weak>
        Controller type. 'weak' is equivalent to setting -W argument.

        Default: strict

      -e eps
        Relative tolerance to determine convergence.

        Default: 1e-2

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
    WEAK_COMPARISON = False
    CONTROLLER_TYPE = "strict"
    EPSILON = 1e-2

    MINS = 60

    PRODUCER1_DELAY = (5 * MINS, 1 * MINS)
    PRODUCER2_DELAY = (10 * MINS, 3 * MINS)
    PRODUCER1_LABEL = 1
    PRODUCER2_LABEL = 2
    T0 = 0

    opts, args = getopt.getopt(argv[1:], "r:o:GT:WC:e:")

    for o, a in opts:
        if o == "-r":
            tmp = a.split(",")
            PRODUCER1_DELAY = tuple(float(val) for val in tmp[:2])
            PRODUCER2_DELAY = tuple(float(val) for val in tmp[2:])
        elif o == "-o":
            OUTPUT_FILENAME = a
            OUTPUT_FILE = open(a, "a")
        elif o == "-G":
            GENERATE_GRAPH_AND_EXIT = True
        elif o == "-T":
            SIMULATION_TIME = float(a)
        elif o == "-W":
            WEAK_COMPARISON = True
        elif o == "-C":
            CONTROLLER_TYPE = a
        elif o == "-e":
            EPSILON = float(a)

    if CONTROLLER_TYPE == "weak":
        WEAK_COMPARISON = True

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

    # [[combiner-tr-defs-start]]

    class CombinerTransition(soyutnet.Transition):
        def __init__(self, *args, **kwargs):
            super().__init__(net=net, *args, **kwargs)
            self.arrival_time = []

        async def _process_tokens(self):
            max_id = 0
            arrivals = [0, 0]
            for label in self._tokens:
                ids = self._tokens[label]
                arrivals[label - 1] = max(ids)
                if ids:
                    max_id = max(max_id, arrivals[label - 1])
            for label in self._tokens:
                self._tokens[label] = [max_id] * len(self._tokens[label])
                """Total delay is the max of two branches"""

            self.arrival_time.append(arrivals)

            return await super()._process_tokens()

    # [[combiner-tr-defs-end]]

    # [[stats-list-defs-start]]

    relative_error = lambda a, b: abs((a - b) / b)

    class NormalSamples(UserList):
        def __init__(self, *args, eps=1e-2, convergence_condition=10, rng_params=None):
            super().__init__(*args)
            self._eps = eps
            self._moments = None
            self._variance = (0, eps, 0.0)
            self._cc = convergence_condition
            self._rng_params = None
            if rng_params is not None:
                self.set_rng_params(rng_params)
            self._max_size = 600 * 1024 * 1024
            self._initialize_moments()
            self._iter = 0

            # [[stats-list-defs-end]]

        def _initialize_moments(self):
            self._moments = [(0.0, self._eps, 0.0), (0.0, self._eps, 0.0)]

        def set_rng_params(self, rng_params):
            self._rng_params = tuple(rng_params) + (rng_params[-1] ** 2,)
            self.clear()
            self._initialize_moments()
            """Reset state"""

        # [[estimation-defs-start]]

        def _update_moment(self, moment, val):
            if abs(val) < 1e-2 * self._eps:
                """Ignore very small numbers in statistics"""
                return moment
            l = len(self)
            mu, eps, eps0 = moment
            if l % self._cc == 0:
                eps0 = 0.0
            mu_prev = mu
            mu = (mu * l + val) / (l + 1)
            dmu = relative_error(mu_prev, mu)
            eps = (eps * l + dmu) / (l + 1)
            eps0 = max(eps0, eps)
            """
            Save the max of last self._cc samples which
            will be used for deciding convergence later.
            """

            return (mu, eps, eps0)

        # [[estimation-defs-end]]

        def _update_moments(self, val):
            """Real-time mean, variance estimation"""
            self._moments[0] = self._update_moment(self._moments[0], val)
            val -= self._moments[0][0]
            self._variance = self._update_moment(self._variance, val**2)
            self._moments[1] = tuple(
                a**2 + b for a, b in zip(self._moments[0], self._variance)
            )

        def _compare_to_actual(self, moment, actual):
            return relative_error(moment[0], actual) < self._eps

        def _size(self):
            return sys.getsizeof(self)

        def append(self, val):
            self._update_moments(val)
            super().append(val)
            self._iter += 1

        def mean(self):
            """
            If max of last self._cc samples are less than self._eps and
            last sample is close to the expected value, it converged.
            """
            mu = self._moments[0][0]
            conv = self._moments[0][2] < self._eps
            if self._rng_params is not None:
                conv &= relative_error(mu, self._rng_params[0]) < self._eps
            return (mu, conv or self._size() >= self._max_size)

        def variance(self):
            """
            If max of last self._cc samples are less than self._eps and
            last sample is close to the expected value, it converged.
            """
            var = self._variance[0]
            conv = self._variance[2] < self._eps
            if self._rng_params is not None:
                conv &= relative_error(var, self._rng_params[2]) < self._eps
            return (var, conv or self._size() >= self._max_size)

        def get_stats(self):
            stats = OrderedDict()
            mu = int(self._moments[0][0])
            std = int(self._variance[0] ** 0.5)
            if self._rng_params is None:
                return output
            mu0, std0 = [int(val) for val in self._rng_params[:2]]
            e1 = relative_error(mu, mu0)
            e2 = relative_error(std, std0)
            precision = round(math.log10(1.0 / self._eps)) + 1
            stats = OrderedDict(
                [
                    ("iter", self._iter),
                    ("mu", mu),
                    ("mu0", mu0),
                    ("Dmu", round(e1, precision)),
                    ("std", std),
                    ("std0", std0),
                    ("Dstd", round(e2, precision)),
                ]
            )

            return stats

        def __str__(self):
            stats = self.get_stats()
            output = ""
            for key in stats:
                output += f"{key}: {stats[key]} "
            return output

    class TimeInstants(NormalSamples):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        def __getitem__(self, n):
            """
            Overriden to return 0 or the last time instant when there
            are less samples than n in the list.
            """
            l = len(self)
            if n < -l:
                return 0
            n = min(n, l - 1)
            return self.data[n]

    # [[controller-state-defs-start]]

    class State(Enum):
        OBSERVE_JOINT_DIST = auto()
        TEST_PRODUCER1 = auto()
        TEST_PRODUCER2 = auto()
        ESTIMATE_DELAYS = auto()
        DONE = auto()

    # [[controller-state-defs-end]]

    class Controller:
        def __init__(self, weak=WEAK_COMPARISON, eps=EPSILON, production_time=None):
            self._mu = 0
            self._std = 0
            self._production_delay = NormalSamples(rng_params=(0, 0), eps=EPSILON)
            self._update_rng_params((0, 0))
            self._mu0 = self._mu
            self._std0 = self._std
            self._state = [State.OBSERVE_JOINT_DIST] * 2
            self._observed = []
            self._u = (0, 0)
            self._slow_producer = (0, 0.0)
            self._weak = weak
            self._production_time = production_time

        def _update_rng_params(self, u):
            """Update expected mean, var of self._production_delay"""
            rng1 = (PRODUCER1_DELAY[0] + u[0], PRODUCER1_DELAY[1])
            rng2 = (PRODUCER2_DELAY[0] + u[1], PRODUCER2_DELAY[1])
            self._mu = results.joint_mean(rng1, rng2)
            self._std = results.joint_variance(rng1, rng2) ** 0.5
            self._production_delay.set_rng_params((self._mu, self._std))

        def _change_state(self, next_state):
            """Change state while saving the previous"""
            self._state = [next_state] + self._state[:-1]
            print(f"{self._state[1]} => {self._state[0]}")
            if next_state != State.DONE and self._production_time is not None:
                tmp = self._production_time[-1]
                self._production_time.clear()
                self._production_time.append(tmp)

        def measure(self, dT):
            self._production_delay.append(dT)

        def found(self):
            """
            weak: only compares mu which converges much faster than variance.
            """
            mu, cond1 = self._production_delay.mean()
            sigma, cond2 = self._production_delay.variance()

            return (mu, sigma**0.5, cond1 and (self._weak or cond2))

        def get_stats(self):
            stats = self._production_delay.get_stats()
            stats["slow"] = self._slow_producer[0]
            stats["Dt"] = int(self._slow_producer[1])
            stats["weak"] = int(self._weak)
            stats["eps"] = round(EPSILON, 3)
            stats.move_to_end("eps", last=False)
            stats.move_to_end("weak", last=False)
            return stats

        def is_done(self):
            """Can exit simulation"""
            return self._state[0] == State.DONE

        # [[controller-defs-start]]

        def advance(self):
            """Iterate the controller"""
            match self._state[0]:  # Check current state
                case State.OBSERVE_JOINT_DIST:  # Initial state
                    """1. Validate that total production time is as expected."""
                    mu, std, conv = self.found()
                    if conv:  # Check convergence
                        self._observed.append(self._u + (mu, std))
                        match self._state[-1]:  # Check previous state
                            case State.OBSERVE_JOINT_DIST:
                                self._change_state(State.TEST_PRODUCER1)
                            case State.TEST_PRODUCER1:
                                self._change_state(State.TEST_PRODUCER2)
                            case State.TEST_PRODUCER2:
                                self._change_state(State.ESTIMATE_DELAYS)
                            case State.ESTIMATE_DELAYS:
                                self._change_state(State.DONE)
                case State.TEST_PRODUCER1:
                    """2. Postpone ordering from producer1"""
                    self._u = (self._mu0, 0)
                    self._update_rng_params(tuple(self._u))
                    self._change_state(State.OBSERVE_JOINT_DIST)
                case State.TEST_PRODUCER2:
                    """3. Postpone ordering from producer2"""
                    self._u = (0, self._mu0)
                    self._update_rng_params(tuple(self._u))
                    self._change_state(State.OBSERVE_JOINT_DIST)
                case State.ESTIMATE_DELAYS:
                    """4. Estimate the slow producer"""
                    t0 = self._observed[0][2]
                    test1 = self._observed[1]
                    test2 = self._observed[2]
                    t1 = test1[2] - t0
                    t2 = test2[2] - t0
                    dt = t1 - t2
                    index = int(dt > 0)
                    dt = abs(dt)
                    self._slow_producer = (index + 1, dt)
                    self._u = (0, 0)
                    self._update_rng_params(tuple(self._u))
                    self._change_state(State.OBSERVE_JOINT_DIST)

            return tuple(map(int, self._u))

    # [[controller-defs-end]]

    # [[stock-counter-defs-start]]

    production_time = TimeInstants()
    Ti = lambda k: production_time[k - 1]
    controller = Controller(production_time=production_time)
    converged = asyncio.Condition()

    async def stock_counter(tr):
        nonlocal production_time, converged
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

        dT = Ti(0) - Ti(-1)
        controller.measure(dT)
        u = controller.advance()
        """
        Measured production time and generated the amount of new order delays ``u``.
        u = (dt1, dt2) means that new order to producer1 and 2 will be placed after
        dt1 and dt2 seconds.
        """
        if controller.is_done():
            """If simulation is done inform the canceller."""
            async with converged:
                converged.notify_all()

        for i in range(2):
            """Postpone orders."""
            label = i + 1
            assert len(tr._tokens[label]) == 1
            tr._tokens[label][0] += u[i]

        return True

    # [[stock-counter-defs-end]]

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
        async with converged:
            await converged.wait()
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
                    "CONTROLLER_TYPE": CONTROLLER_TYPE,
                },
                "production_time": production_time.data,
                "arrival_time": t31.arrival_time,
                "controller_stats": controller.get_stats(),
            }
        )
    )

    OUTPUT_FILE.close()
    """Dump results"""

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
from MultiSnooperServer import MultiSnooperServer
from RealSnooperServer import RealSnooper
import random
import logging
import timeit
import numpy as np

import argparse


parser = argparse.ArgumentParser()
parser.add_argument("--snoopers", default=3, type=int)
parser.add_argument("--use-callbacks", action="store_true")

args = parser.parse_args()
TOTAL_SNOOPERS = args.snoopers

snoopers = []
s0 = RealSnooper()
s0.settimeout(1)
snoopers.append(s0)

for _ in range(TOTAL_SNOOPERS-1):
    s = RealSnooper()
    s.settimeout(0.1)
    snoopers.append(s)

multi_snooper = MultiSnooperServer(snoopers)

for i, snooper in enumerate(snoopers):
    snooper.logger = logging.getLogger(f"snooper#{i}")
    snooper.logger.setLevel(logging.INFO)
multi_snooper.logger.setLevel(logging.INFO)

logging.basicConfig(level=logging.INFO)

times = []
N_requests = 1000
N_success = 0

for nb_request in range(N_requests):
    Sr = [random.randint(9, 15) for _ in snoopers]
    t0 = timeit.default_timer()
    packets = multi_snooper.get_messages(Sr, use_callbacks=args.use_callbacks)
    t1 = timeit.default_timer()
    dt = t1-t0
    times.append(dt)
    logging.info(f"Request @ {nb_request} took {dt*1000:.2f}ms")

    for i, packet in enumerate(packets):
        if packet is None:
            logging.warn(f"socket#{i}: Timed out")
            continue

        N_success += 1
        msg_id, msg = packet
        logging.debug(f"socket#{i}: [{msg_id}] {msg.decode('utf-8')}")

times = np.array(times)
logging.info(f"mean={times.mean()*1000:.2f}ms std={times.std()*1000:.2f}ms")
logging.info(f"Got {N_success} replies from {N_requests} requests")

from HostedMultiSnooperServer import HostedMultiSnooperServer
import random
import logging
import timeit
import numpy as np

multi_snooper = HostedMultiSnooperServer()
multi_snooper.logger.setLevel(logging.INFO)

logging.basicConfig(level=logging.INFO)

times = []
N_requests = 1000
N_success = 0

for nb_request in range(N_requests):
    Sr = [20 for _ in range(multi_snooper.TOTAL_SNOOPERS)]
    t0 = timeit.default_timer()
    packets = multi_snooper.get_messages(Sr)
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

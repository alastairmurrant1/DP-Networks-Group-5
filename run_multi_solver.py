# %% Setup logger
import logging

from RealSnooperServer import RealSnooper

file_logger = logging.FileHandler('solver_multi_v1.log')
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s.%(msecs)03d:%(levelname)s:%(name)s:%(message)s', datefmt="%H:%M:%S")
file_logger.setFormatter(formatter)

logging.basicConfig(handlers=[file_logger, console])
logging.getLogger().setLevel(logging.DEBUG)

# %% Script for testing our different solvers
from importlib import reload

import MultiSnooperServer
import RealSnooperServer
import RealPostServer
import SolverV1_Multi
import PacketSniper

# fresh reload the module if we are updating it while testing
reload(MultiSnooperServer)
reload(RealSnooperServer)
reload(RealPostServer)
reload(SolverV1_Multi)
reload(PacketSniper)

from MultiSnooperServer import MultiSnooperServer
from RealPostServer import RealPostServer
from RealSnooperServer import RealSnooper
from SolverV1_Multi import Solver_V1_Multi as Solver
from PacketSniper import PacketSniper

# %% Startup the real snooper server
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--total-snoopers", default=10, type=int)
args = parser.parse_args()

# Setup child snoopers
# run this locally
snoopers = []
s0 = RealSnooper()
s0.settimeout(0.1)
snoopers.append(s0)

for _ in range(args.total_snoopers-1):
    s = RealSnooper()
    s.settimeout(0.1)
    snoopers.append(s)

# snooper echos have only 1 response
# since we don't really have async code, we just collect the responses in order
# thus the delay from the previous snooper in the list will add up 
# s1 = RealSnooper(SERVER_IP_ADDR="localhost", SERVER_PORT=8889)
# s1.TOTAL_REPLIES = 1
# s1.settimeout(0.5)
# s2 = RealSnooper(SERVER_IP_ADDR="localhost", SERVER_PORT=8920)
# s2.TOTAL_REPLIES = 1
# s2.settimeout(0.25)

for i, snooper in enumerate(snoopers):
    snooper.logger = logging.getLogger(f"snooper#{i}")
    snooper.logger.setLevel(logging.INFO)

# Create parent snooper
snooper_server = MultiSnooperServer(snoopers)
post_server = RealPostServer()

# %% Run our solver against this
messages = []
snipers = [PacketSniper() for _ in range(snooper_server.TOTAL_SNOOPERS)]

while True:
    solver = Solver(snooper_server, snipers)
    solver.logger.setLevel(logging.DEBUG)
    
    final_msg = solver.run(sparse_guess=True)
    messages.append(final_msg)

    res = post_server.post_message(final_msg)
    if res < 400:
        logging.info(f"Message correct @ {solver.total_requests}")
    else:
        logging.error("Got an incorrect message")
        break
        
    if res == 205:
        break

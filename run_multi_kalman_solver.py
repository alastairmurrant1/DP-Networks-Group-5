# %%
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("server_rate", type=int)
parser.add_argument("--use-feeders", action="store_true")
parser.add_argument("--total-snoopers", default=3, type=int)
parser.add_argument("--server-ip-addr", default="149.171.36.192")
parser.add_argument("--server-port", default=8319, type=int)

args = parser.parse_args()

# Calculate server timeout based on the server rate
# The time it takes for 1000 characters to be passed and channel to have queue incremented
SERVER_TIMEOUT = 1000 / args.server_rate

# %% Setup logger
import logging

file_logger = logging.FileHandler('solver_v1.log', mode='w+')
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s.%(msecs)03d:%(levelname)s:%(name)s:%(message)s', datefmt="%H:%M:%S")
file_logger.setFormatter(formatter)

logging.basicConfig(handlers=[console])
logging.getLogger().setLevel(logging.DEBUG)

# %% Script for testing our different solvers
from importlib import reload
import RealSnooperServer
import RealPostServer
import TestSnooperServer
import SolverV1_MultiKalman
import PacketSniper

# fresh reload the module if we are updating it while testing
reload(SolverV1_MultiKalman)
reload(RealSnooperServer)
reload(RealPostServer)
reload(TestSnooperServer)
reload(PacketSniper)

from RealSnooperServer import RealSnooper
from RealPostServer import RealPostServer
from SolverV1_MultiKalman import Solver_V1_MultiKalman as Solver
from PacketSniper import PacketSniper

# %% Startup the real snooper server
# use external snooping servers
# NOTE: Use this in production
if args.use_feeders:
    s0 = RealSnooper(SERVER_IP_ADDR="localhost", SERVER_PORT=8921)
    s1 = RealSnooper(SERVER_IP_ADDR="34.87.197.254", SERVER_PORT=8889)
    s2 = RealSnooper(SERVER_IP_ADDR="34.116.69.217", SERVER_PORT=8920)
    snoopers = [s0,s1,s2]
# use servers on same thread
# NOTE: Cannot use this in production
else:
    snoopers = []
    for _ in range(args.total_snoopers):
        snooper = RealSnooper(SERVER_IP_ADDR=args.server_ip_addr, SERVER_PORT=args.server_port)
        snoopers.append(snooper)

for i, snooper in enumerate(snoopers):
    snooper.settimeout(SERVER_TIMEOUT)
    snooper.logger = logging.getLogger(f"snooper#{i}")
    snooper.logger.setLevel(logging.ERROR)

post_server = RealPostServer(SERVER_IP_ADDR=args.server_ip_addr, SERVER_PORT=args.server_port+1)

# %% Run our solver against this
messages = []
snipers = [PacketSniper(maxlen=10) for _ in range(3)]

logging.info(f"Starting solve with rate={args.server_rate}")

while True:
    solver = Solver(snoopers, snipers, args.server_rate)
    solver.logger.setLevel(logging.DEBUG)
    
    final_msg = solver.run()
    messages.append(final_msg)

    res = post_server.post_message(final_msg)
    if res < 400:
        logging.info(f"Message correct")
    else:
        logging.error("Got an incorrect message")
        break
        
    if res == 205:
        break
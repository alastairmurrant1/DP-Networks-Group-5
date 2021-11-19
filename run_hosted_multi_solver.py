"""
Run the multi solver with the multisnooper server hosted on a local socket
"""
# %%
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--multi-ip-addr", default="localhost")
parser.add_argument("--multi-port", default=33434, type=int)
parser.add_argument("--post-ip-addr", default="149.171.36.192")
parser.add_argument("--post-port", default=8320, type=int)

args = parser.parse_args()

# %% Setup logger
import logging

from RealSnooperServer import RealSnooper

file_logger = logging.FileHandler('solver_hosted_multi_v1.log', mode='w+')
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s.%(msecs)03d:%(levelname)s:%(name)s:%(message)s', datefmt="%H:%M:%S")
file_logger.setFormatter(formatter)

logging.basicConfig(handlers=[file_logger, console])
logging.getLogger().setLevel(logging.DEBUG)

# %% Script for testing our different solvers
from HostedMultiSnooperServer import HostedMultiSnooperServer
from RealPostServer import RealPostServer
from RealSnooperServer import RealSnooper
from SolverV1_Multi import Solver_V1_Multi as Solver
from PacketSniper import PacketSniper

# Create parent snooper
snooper_server = HostedMultiSnooperServer(HOST=args.multi_ip_addr, PORT=args.multi_port)
snooper_server.settimeout(1.5)
post_server = RealPostServer(SERVER_IP_ADDR=args.post_ip_addr, SERVER_PORT=args.post_port)

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

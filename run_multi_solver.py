# %% Setup logger
import logging

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
import RealPostServer
import SolverV1_Multi
import PacketSniper

# fresh reload the module if we are updating it while testing
reload(MultiSnooperServer)
reload(RealPostServer)
reload(SolverV1_Multi)
reload(PacketSniper)

from MultiSnooperServer import MultiSnooperServer
from RealPostServer import RealPostServer
from SolverV1_Multi import Solver_V1_Multi as Solver
from PacketSniper import PacketSniper

# %% Startup the real snooper server
snooper_server = MultiSnooperServer()
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

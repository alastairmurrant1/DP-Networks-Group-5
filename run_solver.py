# %% Setup logger
import logging

file_logger = logging.FileHandler('solver_v1.log')
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)

logging.basicConfig(handlers=[file_logger, console])
logging.getLogger().setLevel(logging.DEBUG)

# %% Script for testing our different solvers
from importlib import reload
import RealSnooperServer
import TestSnooperServer
import SolverV1
import PacketSniper

# fresh reload the module if we are updating it while testing
reload(SolverV1)
reload(RealSnooperServer)
reload(TestSnooperServer)
reload(PacketSniper)

from RealSnooperServer import RealSnooper
from TestSnooperServer import TestSnooper
from SolverV1 import Solver_V1 as Solver
from PacketSniper import PacketSniper

# %% Startup the real snooper server
snooper = RealSnooper(SERVER_PORT=8323)

# %% Startup a test server
snooper = TestSnooper([
    "This is the first message\nAnd this is part of the first message",
    "Hello world\n",
    "This is the third message but quite long\n "*100,
])


# %% Run our solver against this
messages = []
sniper = PacketSniper()

while True:
    solver = Solver(snooper, sniper)
    solver.logger.setLevel(logging.DEBUG)
    
    final_msg = solver.run()
    messages.append(final_msg)

    res = snooper.post_message(final_msg)
    if res < 400:
        logging.info("Message correct\n\n")
    else:
        logging.error("Got an incorrect message\n\n")
        break
        
    if res == 205:
        break

# %% Visualise the sniping errors
import matplotlib.pyplot as plt

print(sniper.net_counts)
net_pdf = sniper.net_PDF
net_pdf = {k:v for k,v in net_pdf.items() if v > 0.001}
print(net_pdf)

plt.figure()
plt.bar(list(net_pdf.keys()), list(net_pdf.values()))
plt.grid(True)


# %%

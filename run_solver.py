# %% Setup logger
import logging

file_logger = logging.FileHandler('solver_v1.log')
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s.%(msecs)03d:%(levelname)s:%(name)s:%(message)s', datefmt="%H:%M:%S")
file_logger.setFormatter(formatter)

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
from TestSnooperServer import TestSnooper, OffsetGenerator
from SolverV1 import Solver_V1 as Solver
from PacketSniper import PacketSniper

# %% Startup the real snooper server
snooper = RealSnooper(SERVER_PORT=8323)

# %% Startup a test server
snooper = TestSnooper([
    "This is the first message\nAnd this is part of the first message",
    "Hello world\n",
    "This is the third message but quite long\n "*100,
    "o"*5000,
])

snooper.offset_generator = OffsetGenerator()

# %% Run our solver against this
messages = []
sniper = PacketSniper()

while True:
    solver = Solver(snooper, sniper)
    solver.logger.setLevel(logging.INFO)
    
    final_msg = solver.run(sparse_guess=True)
    messages.append(final_msg)

    res = snooper.post_message(final_msg)
    if res < 400:
        logging.info(f"Message correct @ {solver.total_requests}")
    else:
        logging.error("Got an incorrect message")
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


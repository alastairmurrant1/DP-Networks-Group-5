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
snooper = RealSnooper(SERVER_PORT=8320, SERVER_AUTH_PORT=8321)

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

    solver.PRINT_INFO = True
    solver.PRINT_DEBUG = True
    
    final_msg = solver.run()
    messages.append(final_msg)

    res = snooper.post_message(final_msg)
    if res < 400:
        print("[SUCCESS] Message correct\n\n")
    else:
        print("[ERROR] Got an incorrect message\n\n")
        break
        
    if res == 205:
        break

# %% Visualise the sniping errors
import matplotlib.pyplot as plt

print(sniper.net_counts)
net_pdf = sniper.net_PDF
print(net_pdf)

plt.figure()
plt.bar(list(net_pdf.keys()), list(net_pdf.values()))
plt.grid(True)


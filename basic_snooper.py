#%%
import socket
import struct
import random

import matplotlib.pyplot as plt
import numpy as np

# %% Setup the socket
try:
    sock.close()
except NameError:
    pass
finally:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(10)

# %% Our server details
# To setup the server we do the following
# 1. SSH via 'ssh -X np14@149.171.36.192'
# 2. Login via our password
# 3. Run the command '4123-server -address 0.0.0.0 -port 8319 -file message.txt'

# 0.0.0.0 means the server will listen to all IPv4 addresses

SERVER_IP_ADDR = "149.171.36.192"
SERVER_PORT = 8319
SERVER_AUTH_PORT = SERVER_PORT+1

# %% Get messages from server
Pr = random.randint(1, 1 << 31)
Sr = 9
datagram = struct.pack(">LL", Sr, Pr)

messages = []

for i in range(1000):
    sock.sendto(datagram, (SERVER_IP_ADDR, SERVER_PORT))
    try:
        data = sock.recv(1024)
        data = sock.recv(1024) # due to duplication of udp response
    except socket.timeout:
        print("Timed out")
        break

    Pt, msg_id = struct.unpack(">LL", data[:8])
    msg = data[8:]
    
    if Pr != Pt:
        print(f"Mismatching Pr (sent {Pr}, got {Pt})")
        continue

    msg_str = str(msg, 'ascii').replace('\n', '')
    print(f"\r[{i}] [{msg_id}] {msg_str:20s}", end='')
    messages.append((msg_id, msg))

# %% Show distribution of differences between message ids
# Ignore the first two because they are potentially from previous message
msg_ids = np.array([m[0] for m in messages])
msg_ids = msg_ids[2:]
msg_ids = msg_ids - msg_ids.min()
deltas = msg_ids[1:]-msg_ids[:-1]
print(np.mean(deltas), np.std(deltas))
plt.hist(deltas)

# %% Show distribution of message lengths
msg_lengths = np.array([len(m[1]) for m in messages])
print(np.mean(msg_lengths), np.std(msg_lengths))
plt.hist(msg_lengths)

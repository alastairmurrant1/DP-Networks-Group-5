"""
Test dual shot packet sniping
This involves sending two packets consecutively with no pause
The server will receive them at the same time with no delay
Thus we can snipe with the distance between two shots being accurate
"""
# %%
import socket
import random
import argparse
import timeit

parser = argparse.ArgumentParser()
parser.add_argument("--server-ip-addr", default="149.171.36.192", help="IP address of host")
parser.add_argument("--server-port", default=8319, type=int, help="Port of host")
parser.add_argument("--count", default=10, type=int, help="Number of requests to send")
parser.add_argument("--max-ping", default=250, type=int, help="Maximum ping in ms before timeout")
parser.add_argument("--max-retries", default=2, type=int, help="Maximum number of replies to recieve on single request")

args = parser.parse_args([])

def construct_packet_request(Sr, Pr):
    return Sr.to_bytes(4, byteorder="big") + Pr.to_bytes(4, byteorder="big")

def decode_packet_response(data):
    Pt = int(data[:4].hex(), 16)
    msg_id = int(data[4:8].hex(), 16)
    msg = data[8:]
    return (Pt, msg_id, msg)

# %%
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(float(args.max_ping) / 1000)
sock.connect((args.server_ip_addr, args.server_port))
print(f"Pinging UDP to {args.server_ip_addr}:{args.server_port}")

# %%
d1 = construct_packet_request(10, 1024)
d2 = construct_packet_request(1, 1025)
d = d1+d2

sock.sendall(d1)
sock.sendall(d2)

# %%
try:
    while True:
        rx = sock.recv(1024)
        rx = decode_packet_response(rx)
        print(rx)
except socket.timeout:
    pass

# %%
import numpy as np
import random

packets = []

# %%
Sr = random.randint(8, 12)
Pr = random.randint(1, 1 << 31)

for _ in range(10000):
    d1 = construct_packet_request(Sr, Pr)
    sock.sendall(d1)

    try:
        while True:
            rx = sock.recv(1024)
            rx = decode_packet_response(rx)
            if rx[0] == Pr:
                packets.append(rx)
                break
    except socket.timeout:
        pass

# %%
L = np.array([len(rx[2]) for rx in packets])

import matplotlib.pyplot as plt
plt.hist(L)


# %%
R = 1000
ping = 10e-3
char = R * ping


# %%
for N in (1, 2, 3, 5, 10, 20, 30, 100):
    nb_samples = 1000
    x = np.zeros((nb_samples, 1))

    for _ in range(N):
        r = np.random.randint(4, 21, (nb_samples, 1))
        x += r
    
    x = x / 12 
    # x = (x - N*12) / (4.9*(N**0.5))
    print(x.std() / (N**0.5))

    # plt.hist(x, bins=np.arange(x.min(), x.max()+2), density=True)
    plt.hist(x, density=True, bins=20, alpha=0.2, label=f"{N}")

plt.legend()
# plt.axvline(N*12, color="r")

# %%
for C in np.array([1,2,3,5,10,20,30,100])*12:
    nb_samples = 1000
    c = np.zeros((nb_samples, 1))
    x = np.zeros((nb_samples, 1))

    while True:
        r = np.random.randint(4, 21, (nb_samples, 1))
        mask = (c < C).astype(np.int)
        if mask.sum() == 0:
            break
        r = r * mask

        c += r
        x += mask

    # N = C // 12 
    # x = (x - N) / (0.41 * (N**0.5))
    # print(x.std())

    plt.hist(x, density=True, bins=np.arange(np.floor(x.min()), np.ceil(x.max())+2), alpha=0.2, label=f"{C}")

plt.legend()


# %% Model how std adds up
N1 = 4
sd1 = 0.41*(N1**0.5)

N2 = 1 
sd2 = 0.41*(N2**0.5)

nb_samples = 10000

x = np.zeros((nb_samples, 1))

for N in (N1, N2):
    sd = 0.41*(N**0.5)
    r = np.random.normal(N, sd, size=(nb_samples, 1))
    x += r

print(x.mean())
print(x.std())

# %%
x = np.random.normal(10, 0.1, (1000, 1))
print(x.mean(), x.std())

x = x/10
print(x.mean(), x.std())

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

# %% Startup teh socket server for testing
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(float(args.max_ping) / 1000)
sock.connect((args.server_ip_addr, args.server_port))
print(f"Pinging UDP to {args.server_ip_addr}:{args.server_port}")

# %% Transmit our double shot
d1 = construct_packet_request(10, 1024)
d2 = construct_packet_request(1, 1025)
d = d1+d2

sock.sendall(d1)
sock.sendall(d2)

# %% Attempt to recieve our double shot
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
import matplotlib.pyplot as plt

# %%
packets = []
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

# %% Plot distribution of our packet lengths
L = np.array([len(rx[2]) for rx in packets])
plt.hist(L)

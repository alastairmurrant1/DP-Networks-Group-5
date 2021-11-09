# %%
import socket
import random

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

def construct_request(Sr, Pr):
    return Sr.to_bytes(4, byteorder="big") + Pr.to_bytes(4, byteorder="big")

def decode_response(data):
    Pt = int(data[:4].hex(), 16)
    msg_id = int(data[4:8].hex(), 16)
    msg = data[8:]
    
    return (Pt, msg_id, msg)

# %% Send a snooper request
Pr = random.randint(1, 1 << 31)
Sr = 9
datagram = construct_request(Sr, Pr)

messages = []

for _ in range(1000):
    sock.sendto(datagram, (SERVER_IP_ADDR, SERVER_PORT))
    try:
        data = sock.recv(1024)
        data = sock.recv(1024) # due to duplication of udp response
    except socket.timeout:
        print("Timed out")
        break
    
    Pt, msg_id, msg = decode_response(data)
    
    if Pr != Pt:
        print(f"Mismatching Pr (sent {Pr}, got {Pt})")
        continue
    
    print(f"[{msg_id}] [len={len(msg)}] {str(msg, 'ascii')}")
    messages.append((msg_id, msg))
# %%

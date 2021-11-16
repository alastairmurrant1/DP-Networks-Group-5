import socket
import random
import argparse
import timeit

parser = argparse.ArgumentParser()
parser.add_argument("--server-ip-addr", default="149.171.36.192", help="IP address of host")
parser.add_argument("--server-port", default=8319, type=int, help="Port of host")
parser.add_argument("--count", default=10, type=int, help="Number of requests to send")
parser.add_argument("--max-ping", default=250, type=int, help="Maximum ping in ms before timeout")

args = parser.parse_args()

def construct_packet_request(Sr, Pr):
    return Sr.to_bytes(4, byteorder="big") + Pr.to_bytes(4, byteorder="big")

def decode_packet_response(data):
    Pt = int(data[:4].hex(), 16)
    msg_id = int(data[4:8].hex(), 16)
    msg = data[8:]
    return (Pt, msg_id, msg)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(float(args.max_ping) / 1000)
sock.connect((args.server_ip_addr, args.server_port))
print(f"Pinging UDP to {args.server_ip_addr}:{args.server_port}")

all_response_times = []
total_sent = 0
total_replied = 0
total_dups = 0
total_mismatch = 0

def mean(x):
    return sum(x) / len(x)
    
for i in range(args.count):
    Sr = random.randint(8,12)
    Pr = random.randint(1, 1 << 31)
    datagram = construct_packet_request(Sr, Pr)

    responses = []
    response_times = []

    dt_start = timeit.default_timer()
    
    sock.send(datagram)
    total_sent += 1
    while True:
        try:
            data = sock.recv(1024)
            response_times.append(timeit.default_timer())
            responses.append(data)
        except socket.timeout:
            break
    
    if len(response_times) == 0:
        print(f"[{i}] No reply")
        continue

    
    response_times = [t-dt_start for t in response_times]
    all_response_times.extend(response_times)
    res_ms = [t*1000 for t in response_times]

    print(f"[{i}] Reply count={len(response_times)} min={min(res_ms):.2f}ms avg={mean(res_ms):.2f}ms max={max(res_ms):.2f}ms len={len(data)}")

    packets = [decode_packet_response(data) for data in responses]

    found_previous = False
    for Pt, msg_id, msg in packets:
        if Pt != Pr:
            print(f"[WARN] Mismatching Pr={Pr} Pt={Pt} msg_id={msg_id}")
            total_mismatch += 1
            continue

        if not found_previous:
            total_replied += 1
        else:
            total_dups += 1

        found_previous = found_previous or True

sock.close()

res_ms = [t*1000 for t in all_response_times]

if len(res_ms) > 1:
    print(f"Statistics: Reply sent={total_sent} replies={total_replied} dup={total_dups} min={min(res_ms):.2f}ms avg={mean(res_ms):.2f}ms max={max(res_ms):.2f}ms")
else:
    print(f"Statistics: No replies")
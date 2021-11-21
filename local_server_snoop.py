import socket
import logging
import argparse

from RealSnooperServer import RealSnooper
from MultiSnooperServer import MultiSnooperServer

def decode_request(data, total_snoopers):
    assert len(data) == total_snoopers*8
    packets = []
    for i in range(total_snoopers):
        sub_data = data[i*8:(i+1)*8]
        Sr = int.from_bytes(sub_data[:4], "big")
        Pr = int.from_bytes(sub_data[4:8], "big")
        packets.append((Sr, Pr))

    return packets

def encode_responses(responses):
    lengths = bytes([]) 
    data = bytes([]) 
    for response in responses:
        if response is None:
            lengths += int(0).to_bytes(4, "big")
            continue
            
        Pr, msg_id, msg = response
        lengths += int(8+len(msg)).to_bytes(4, "big")
        data += int(Pr).to_bytes(4, "big") + int(msg_id).to_bytes(4, "big") + msg
    
    return lengths + data

# handle request for number of snoopers running 
def handle_total_snoopers_request(total_snoopers):
    return int.to_bytes(total_snoopers, 4, "big")

# handle request for array of (Sr, Pr)
def handle_snooper_request(request, multi_snooper):
    total_snoopers = multi_snooper.TOTAL_SNOOPERS
    packets = decode_request(request, total_snoopers)
    logging.debug(f"Got packets: {packets}")

    Sr_arr = [Sr for Sr, Pr in packets]
    Pr_arr = [Pr for Sr, Pr in packets]

    packets = multi_snooper.get_messages(Sr_arr=Sr_arr, Pr_arr=Pr_arr)

    # add Pr back to responses
    responses = []
    for Pr, packet in zip(Pr_arr, packets):
        if packet is None:
            responses.append(None)
        else:
            msg_id, msg = packet
            responses.append((Pr, msg_id, msg))

    response_datagram = encode_responses(responses)
    return response_datagram

def handle_request(request, sock, addr, multi_snooper):
    logging.debug(f"Got request from {addr}")

    if request == int("DEADBEEFDEADBEEF", 16).to_bytes(8, "big"):
        logging.info(f"Replying with total_snoopers={multi_snooper.TOTAL_SNOOPERS}")
        response_datagram = handle_total_snoopers_request(multi_snooper.TOTAL_SNOOPERS)
    else:
        response_datagram = handle_snooper_request(request, multi_snooper)

    sock.sendto(response_datagram, addr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--use-feeders", action="store_true")
    parser.add_argument("--total-snoopers", default=3, type=int)
    parser.add_argument("--server-ip-addr", default="149.171.36.192", type=str)
    parser.add_argument("--server-port", default=8319, type=int)
    parser.add_argument("--server-timeout", default=200, type=int)

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    #Server Host
    HOST_SERV = 'localhost'                 
    PORT_SERV = 33434  

    # use external snooping servers
    # NOTE: Use this in production
    if args.use_feeders:
        s0 = RealSnooper(SERVER_IP_ADDR=args.server_ip_addr, SERVER_PORT=args.server_port)
        s1 = RealSnooper(SERVER_IP_ADDR="34.87.197.254", SERVER_PORT=8889)
        s2 = RealSnooper(SERVER_IP_ADDR="34.116.69.217", SERVER_PORT=8920)
        snoopers = [s0,s1,s2]
    # use servers on same thread
    # NOTE: Cannot use this in production
    else:
        snoopers = []
        for _ in range(args.total_snoopers):
            snooper = RealSnooper(SERVER_IP_ADDR=args.server_ip_addr, SERVER_PORT=args.server_port)
            snoopers.append(snooper)

    # label each snooper for logging 
    for i, snooper in enumerate(snoopers):
        snooper.logger = logging.getLogger(f"snooper#{i}")
        snooper.logger.setLevel(logging.DEBUG)
        snooper.settimeout(args.server_timeout / 1000)
    
    multi_snooper = MultiSnooperServer(snoopers)
    multi_snooper.logger.setLevel(logging.DEBUG)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST_SERV, PORT_SERV))

    logging.info(f"Starting server at {HOST_SERV}:{PORT_SERV}")
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            if not data:
                logging.info(f"Client {addr} disconnected")
                break
            
            handle_request(data, sock, addr, multi_snooper)
        except socket.timeout:
            logging.warning(f"Timed out")
    
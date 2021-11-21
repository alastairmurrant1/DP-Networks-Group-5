from HostedMultiSnooperServer import HostedMultiSnooperServer
import logging
import random
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--server-ip-addr", default="localhost")
parser.add_argument("--server-port", default=33434, type=int)

args = parser.parse_args()

logging.basicConfig(level=logging.DEBUG)
snooper = HostedMultiSnooperServer(HOST=args.server_ip_addr, PORT=args.server_port)

Sr_arr = [random.randint(12, 20)     for _ in range(snooper.TOTAL_SNOOPERS)]
Pr_arr = [random.randint(1, 1 << 31) for _ in range(snooper.TOTAL_SNOOPERS)]

packets = snooper.get_messages(Sr_arr, Pr_arr)

for i, (packet, Sr, Pr) in enumerate(zip(packets, Sr_arr, Pr_arr)):
    if packet is None:
        logging.info(f"socket#{i}: timed out")
        continue
    
    msg_id, msg = packet
    logging.info(f"socket#{i}: MsgID={msg_id} Pr={Pr} Sr={Sr} Length={len(msg)} Message={msg.decode('utf-8')}")
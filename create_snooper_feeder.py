#Sends socket requests to server backdoor and sends packets to snoop middle man
# Uses UDP
# Need to update using only sockets
import socket
from RealSnooperServer import RealSnooper

import logging

def handle_request(request, sock, addr, snooper):
    received = 0
    received = received.to_bytes(4,byteorder="big")

    Sr = int.from_bytes(request[:4], "big")
    Pr = int.from_bytes(request[4:8], "big")

    logging.debug(f"Received Sr={Sr} Pr={Pr}")

    try:
        msg_id, msg = snooper.get_message(Sr, Pr)
        logging.debug(f"Reply [{msg_id}] {msg.decode('utf-8')}")
        received = Pr.to_bytes(4, "big") + msg_id.to_bytes(4, "big") + msg
    except socket.timeout:
        logging.warn('Timeout')
        
    sock.sendto(received, addr)

class FeederServer:
    def __init__(self, sock, snooper, logger=None):
        self.sock = sock
        self.snooper = snooper
        self.logger = logger or logging.getLogger("FeederServer")
    
    def run(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(1024)
                if not data:
                    logging.info(f"Client {addr} disconnected")
                    break
                
                handle_request(data, self.sock, addr, self.snooper)
            except socket.timeout:
                self.logger.warning(f"Timed out")

def create_snooper_feeder(HOST, PORT):
    logging.info(f"Creating feed server on {HOST}:{PORT}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    snooper = RealSnooper()

    feeder = FeederServer(sock, snooper)
    return feeder
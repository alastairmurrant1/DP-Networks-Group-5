#Sends socket requests to server backdoor and sends packets to snoop middle man
#Socketserver is used to receive Sr from RealSnooperServer
# Uses UDP
# Need to update using only sockets
import socket,socketserver
from RealSnooperServer import RealSnooper

import logging

class UDPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        request = self.request[0]
        client_socket = self.request[1]
        received = 0
        received = received.to_bytes(4,byteorder="big")

        Sr = int.from_bytes(request[:4], "big")
        Pr = int.from_bytes(request[4:8], "big")

        logging.debug(f"Received Sr={Sr} Pr={Pr}")

        try:
            msg_id, msg = self.server.snooper.get_message(Sr, Pr)
            logging.debug(f"Reply [{msg_id}] {msg.decode('utf-8')}")
            received = Pr.to_bytes(4, "big") + msg_id.to_bytes(4, "big") + msg
        except socket.timeout:
            logging.warn('Timeout')
            
        client_socket.sendto(received, self.client_address)


def create_snooper_feeder(HOST, PORT):
    logging.info(f"Creating feed server on {HOST}:{PORT}")
    server = socketserver.UDPServer((HOST, PORT), UDPRequestHandler)
    #Set up Socket
    server.snooper = RealSnooper()
    return server
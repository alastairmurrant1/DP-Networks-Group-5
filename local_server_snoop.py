import socket
import socketserver
import logging
import argparse

from RealSnooperServer import RealSnooper
from MultiSnooperServer import MultiSnooperServer

def decode_request(data):
    assert len(data) == 24

    packets = []
    for i in range(3):
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

class UDPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        request = self.request[0]
        client_socket = self.request[1]

        logging.debug(f"Got request from {self.client_address}")

        packets = decode_request(request)
        assert len(packets) == len(snoopers)
        logging.debug(f"Got packets: {packets}")

        Sr_arr = [Sr for Sr, Pr in packets]
        Pr_arr = [Pr for Sr, Pr in packets]
        use_callbacks = self.server.env_args.use_callbacks

        packets = self.server.multi_snooper.get_messages(Sr_arr=Sr_arr, Pr_arr=Pr_arr, use_callbacks=use_callbacks)

        # add Pr back to responses
        responses = []
        for Pr, packet in zip(Pr_arr, packets):
            if packet is None:
                responses.append(None)
            else:
                msg_id, msg = packet
                responses.append((Pr, msg_id, msg))

        response_datagram = encode_responses(responses)
        client_socket.sendto(response_datagram, self.client_address)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--use-callbacks", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    #Server Host
    HOST_SERV = 'localhost'                 
    PORT_SERV = 33434  

    # run this locally
    s0 = RealSnooper()
    # snooper echos have only 1 response
    s1 = RealSnooper(SERVER_IP_ADDR="localhost", SERVER_PORT=8889)
    s1.TOTAL_REPLIES = 1
    s2 = RealSnooper(SERVER_IP_ADDR="localhost", SERVER_PORT=8920)
    s2.TOTAL_REPLIES = 1
    
    snoopers = [s0, s1, s2]
    for i, snooper in enumerate(snoopers):
        snooper.logger = logging.getLogger(f"snooper#{i}")
    
    multi_snooper = MultiSnooperServer(snoopers)

    logging.info(f"Starting local snooping server on {HOST_SERV}:{PORT_SERV}") 
    server = socketserver.UDPServer((HOST_SERV, PORT_SERV), UDPRequestHandler)
    server.multi_snooper = multi_snooper
    server.env_args = args

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        server.server_close()
        
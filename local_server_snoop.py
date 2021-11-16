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

        if request == int("DEADBEEFDEADBEEF", 16).to_bytes(8, "big"):
            logging.info(f"Replying with total_snoopers={self.server.multi_snooper.TOTAL_SNOOPERS}")
            response_datagram = self.handle_total_snoopers_request(request)
        else:
            response_datagram = self.handle_snooper_request(request)

        client_socket.sendto(response_datagram, self.client_address)

    # handle request for number of snoopers running 
    def handle_total_snoopers_request(self, request):
        total_snoopers = self.server.multi_snooper.TOTAL_SNOOPERS
        return int.to_bytes(total_snoopers, 4, "big")

    # handle request for array of (Sr, Pr)
    def handle_snooper_request(self, request):
        packets = decode_request(request)
        assert len(packets) == self.server.multi_snooper.TOTAL_SNOOPERS
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
        return response_datagram

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--use-callbacks", action="store_true")
    parser.add_argument("--use-feeders", action="store_true")
    parser.add_argument("--total-local-snoopers", default=3, type=int)

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    #Server Host
    HOST_SERV = 'localhost'                 
    PORT_SERV = 33434  

    # run this locally
    snoopers = []
    s0 = RealSnooper()
    snoopers.append(s0)

    # use external snooping servers
    if args.use_feeders:
        # snooper echos have only 1 response
        s1 = RealSnooper(SERVER_IP_ADDR="localhost", SERVER_PORT=8889)
        s1.TOTAL_REPLIES = 1
        s2 = RealSnooper(SERVER_IP_ADDR="localhost", SERVER_PORT=8920)
        s2.TOTAL_REPLIES = 1
    # use servers on same thread
    # NOTE: Cannot use this in production
    else:
        for _ in range(args.total_local_snoopers-1):
            s = RealSnooper()
            snoopers.append(s)
    
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
        
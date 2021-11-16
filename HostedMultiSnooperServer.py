import socket
import random
import logging

"""
Connects to the local snooper server which communicates with its 3 child servers
"""
class HostedMultiSnooperServer:
    def __init__(self, HOST="localhost", PORT=33434, logger=None):
        self.HOST = HOST
        self.PORT = PORT
        self.TOTAL_SNOOPERS = 3

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(2)

        self.logger = logger or logging.getLogger(__name__)

    # Returns an array of packets
    # A packet is None is that snooping channel has timedout 
    # A packet is defined if that snooping channel replied back
    def get_messages(self, Sr_arr, Pr_arr=None):
        assert len(Sr_arr) == self.TOTAL_SNOOPERS
        if Pr_arr is None:
            Pr_arr = [random.randint(1, 1 << 31) for _ in range(self.TOTAL_SNOOPERS)]
        
        datagram = self.create_request_datagram(list(zip(Pr_arr, Sr_arr)))
        self.sock.sendto(datagram, (self.HOST, self.PORT))

        while True:
            try:
                data = self.sock.recv(2048)
            except socket.timeout as ex:
                self.logger.error("Timed out")
                raise ex
            
            packets = self.decode_packet_response(data)
            for i, (packet, Pr) in enumerate(zip(packets, Pr_arr)):
                if packet is None:
                    self.logger.warn(f"Snooper#{i} timedout")
                    continue

                Pt, _, _ = packet
                if Pt != Pr:
                    self.logger.warn(f"Snooper#{i}: Mismatching Pr (sent {Pr}, got {Pt})")
                    break
            else:
                break

        responses = [] 
        for packet in packets:
            if packet is None:
                responses.append(None)
            else:
                _, msg_id, msg = packet
                responses.append((msg_id, msg))
        return responses

    # send requests to the local snoop server 
    def create_request_datagram(self, requests):
        assert len(requests) == self.TOTAL_SNOOPERS 
        datagram = bytes([])

        for Pr, Sr in requests:
            datagram += Sr.to_bytes(4, byteorder="big") + Pr.to_bytes(4, byteorder="big")
        
        return datagram

    # decode response from the local snoop server 
    def decode_packet_response(self, data):
        response_lengths = []
        SIZEOF_LONG = 4
        for i in range(self.TOTAL_SNOOPERS):
            n = int.from_bytes(data[i*SIZEOF_LONG:(i+1)*SIZEOF_LONG], "big")
            response_lengths.append(n)
        
        data = data[SIZEOF_LONG*self.TOTAL_SNOOPERS:]
        assert len(data) == sum(response_lengths)

        responses = []
        for i, N in enumerate(response_lengths):
            if N == 0:
                responses.append(None)
            else:
                Pt = int.from_bytes(data[:4], "big")
                msg_id = int.from_bytes(data[4:8], "big")
                msg = data[8:N] 
                responses.append((Pt, msg_id, msg))
                data = data[N:]
        
        return responses
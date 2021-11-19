import socket
import random
import logging
from timeit import default_timer

# To setup the server we do the following
# 1. SSH via 'ssh -X np14@149.171.36.192'
# 2. Login via our password
# 3. Run the command '4123-server -address 0.0.0.0 -port 8319 -file message.txt'

class RealSnooper:
    def __init__(self, SERVER_IP_ADDR="149.171.36.192", SERVER_PORT=8319):
        self.SERVER_IP_ADDR = SERVER_IP_ADDR
        self.SERVER_PORT = SERVER_PORT

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(2)

        self.logger = logging.getLogger(__name__)

        self.sock.connect((self.SERVER_IP_ADDR, self.SERVER_PORT))
    
    def settimeout(self, *args, **kwargs):
        self.sock.settimeout(*args, **kwargs)
    
    def close(self):
        self.sock.close()
    
    def _fetch_message(self, Pr, time_sent):
        # run through responses until we get our desired packet
        # duplication or packet losses can occur, which causes this to go out of sync
        msg_id = None

        while True: 
            try:
                data = self.sock.recv(1024)

                # check if last packet contained correct Pr
                try:
                    Pt, msg_id, msg = self.decode_packet_response(data)
                except ValueError:
                    self.logger.error(f"Failed to decode packet: len={len(data)} content={data}")
                    raise socket.timeout()

                if Pt == Pr:
                    break
            except socket.timeout as ex:
                # if no previous replies, then raise timeout error
                if msg_id is None or Pt != Pr:
                    self.logger.error(f"Mismatching Pr (sent {Pr}, got {Pt})")
                    raise ex
                break
        
        assert Pr == Pt

        time_gotten = default_timer()
        rtt = time_gotten - time_sent
        self.logger.debug(f"Matching reply rtt={rtt*1000:.0f}ms (sent {Pr}, got {Pt})")
        return (msg_id, msg)
    
    # get a message from the server with our desired Sr 
    def get_message(self, Sr, Pr=None, return_callback=False):
        if Pr is None:
            Pr = random.randint(1, 1 << 31)

        datagram = self.construct_packet_request(Sr, Pr)
        # self.sock.sendto(datagram, (self.SERVER_IP_ADDR, self.SERVER_PORT))
        
        time_sent = default_timer()
        self.sock.send(datagram)

        if not return_callback:
            return self._fetch_message(Pr, time_sent)
        
        def callback():
            return self._fetch_message(Pr, time_sent)

        return callback


    def construct_packet_request(self, Sr, Pr):
        return Sr.to_bytes(4, byteorder="big") + Pr.to_bytes(4, byteorder="big")

    def decode_packet_response(self, data):
        Pt = int(data[:4].hex(), 16)
        msg_id = int(data[4:8].hex(), 16)
        msg = data[8:]
        return (Pt, msg_id, msg)
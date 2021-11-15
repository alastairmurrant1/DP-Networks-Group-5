import socket
import random
import logging

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

        # if we get duplicates for some reason
        self.TOTAL_REPLIES = 2
    
    def settimeout(self, *args, **kwargs):
        self.sock.settimeout(*args, **kwargs)
    
    def close(self):
        self.sock.close()
    
    def _fetch_message(self, Pr):
        # run through responses until we get our desired packet
        msg_id = None
        while True: 
            try:
                # receive duplicates
                for _ in range(self.TOTAL_REPLIES):
                    data = self.sock.recv(1024)
                
                # check if last packet contained correct Pr
                try:
                    Pt, msg_id, msg = self.decode_packet_response(data)
                except ValueError:
                    raise socket.timeout()

                if Pt == Pr:
                    break
                else:
                    # self.logger.warn(f"Mismatching Pr (sent {Pr}, got {Pt})")
                    continue
            except socket.timeout as ex:
                # if no previous replies, then raise timeout error
                if msg_id is None or Pt != Pr:
                    raise ex
                break
        
        if Pt == Pr:
            self.logger.debug(f"Matching    Pr (sent {Pr}, got {Pt})")
        else:
            self.logger.error(f"Mismatching Pr (sent {Pr}, got {Pt})")
        return (msg_id, msg)

    
    # get a message from the server with our desired Sr 
    def get_message(self, Sr, Pr=None, return_callback=False):
        if Pr is None:
            Pr = random.randint(1, 1 << 31)

        datagram = self.construct_packet_request(Sr, Pr)
        self.sock.sendto(datagram, (self.SERVER_IP_ADDR, self.SERVER_PORT))

        if not return_callback:
            return self._fetch_message(Pr)
        
        def callback():
            return self._fetch_message(Pr)

        return callback


    def construct_packet_request(self, Sr, Pr):
        return Sr.to_bytes(4, byteorder="big") + Pr.to_bytes(4, byteorder="big")

    def decode_packet_response(self, data):
        Pt = int(data[:4].hex(), 16)
        msg_id = int(data[4:8].hex(), 16)
        msg = data[8:]
        return (Pt, msg_id, msg)
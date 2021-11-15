import socket
import random

# To setup the server we do the following
# 1. SSH via 'ssh -X np14@149.171.36.192'
# 2. Login via our password
# 3. Run the command '4123-server -address 0.0.0.0 -port 8319 -file message.txt'

class RealSnooper:
    def __init__(self, SERVER_IP_ADDR="149.171.36.192", SERVER_PORT=8319, SERVER_AUTH_PORT=None):
        self.SERVER_IP_ADDR = SERVER_IP_ADDR
        self.SERVER_PORT = SERVER_PORT

        if SERVER_AUTH_PORT is None:
            SERVER_AUTH_PORT = SERVER_PORT+1
        self.SERVER_AUTH_PORT = SERVER_AUTH_PORT

        self.packet_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.packet_sock.settimeout(2)
    
    def close(self):
        self.packet_sock.close()

    # get a message from the server with our desired Sr 
    def get_message(self, Sr, Pr=None):

        if Pr is None:
            Pr = random.randint(1, 1 << 31)

        datagram = self.construct_packet_request(Sr, Pr)

        self.packet_sock.sendto(datagram, (self.SERVER_IP_ADDR, self.SERVER_PORT))

        try:
            data = self.packet_sock.recv(1024)
            data = self.packet_sock.recv(1024) # due to duplication of udp response
        except socket.timeout as ex:
            raise ex

        Pt, msg_id, msg = self.decode_packet_response(data)

        if Pr != Pt:
            print(f"[WARN] Mismatching Pr (sent {Pr}, got {Pt})")
            #raise ValueError(f"Mismatching Pr (sent {Pr}, got {Pt})")
        
        return (msg_id, msg)

    # post final message to server
    # # returns the status code 
    def post_message(self, message):
        headers = {"Connection": "close"} # close the tcp connection when done
        message = message + chr(0x04)
        res = self.send_post_request(message, headers=headers)
        return res

    def construct_packet_request(self, Sr, Pr):
        return Sr.to_bytes(4, byteorder="big") + Pr.to_bytes(4, byteorder="big")

    def decode_packet_response(self, data):
        Pt = int(data[:4].hex(), 16)
        msg_id = int(data[4:8].hex(), 16)
        msg = data[8:]
        return (Pt, msg_id, msg)

    def decode_post_response(self, res):
        res = str(res, "utf-8")
        lines = res.split("\n")
        header = lines[0].split(' ')
        status_code = int(header[1])
        return status_code

    def construct_post_request_body(self, message, version="1.1", headers={}):
        request = ""
        request += f"POST / HTTP/{version}\r\n"
        request += f"Host: {self.SERVER_IP_ADDR}:{self.SERVER_AUTH_PORT}\r\n"
        
        for k, v in headers.items():
            request += f"{k}: {v}\r\n"
        
        msg_len = len(message)
        
        request += f"Content-Length: {msg_len}\r\n"
        request += "\r\n" + message
        
        return request

    def send_post_request(self, message, headers={}):
        # create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect((self.SERVER_IP_ADDR, self.SERVER_AUTH_PORT))

        request = self.construct_post_request_body(message, headers=headers)
        n = sock.send(bytes(request, "utf-8"))
        
        try:
            data = sock.recv(1024)
            res = self.decode_post_response(data)
            return res
        except socket.timeout:
            return None
        finally:
            sock.close()
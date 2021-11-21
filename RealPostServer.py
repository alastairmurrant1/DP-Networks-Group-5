import socket
import logging

class RealPostServer:
    def __init__(self, SERVER_IP_ADDR="149.171.36.192", SERVER_PORT=8320):
        self.SERVER_IP_ADDR = SERVER_IP_ADDR
        self.SERVER_PORT = SERVER_PORT

        self.logger = logging.getLogger(__name__)

    # post final message to server
    # # returns the status code 
    def post_message(self, message):
        headers = {"Connection": "close"} # close the tcp connection when done
        message = message + chr(0x04)
        res = self.send_post_request(message, headers=headers)
        return res

    def decode_post_response(self, res):
        res = str(res, "utf-8")
        lines = res.split("\n")
        header = lines[0].split(' ')
        status_code = int(header[1])
        return status_code

    def construct_post_request_body(self, message, version="1.1", headers={}):
        request = ""
        request += f"POST / HTTP/{version}\r\n"
        request += f"Host: {self.SERVER_IP_ADDR}:{self.SERVER_PORT}\r\n"
        
        for k, v in headers.items():
            request += f"{k}: {v}\r\n"
        
        msg_len = len(message)
        
        request += f"Content-Length: {msg_len}\r\n"
        request += "\r\n" + message
        
        return request

    def send_post_request(self, message, headers={}, timeout=2):
        # create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((self.SERVER_IP_ADDR, self.SERVER_PORT))

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
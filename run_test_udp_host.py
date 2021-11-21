import socketserver
import argparse
import logging
import random

parser = argparse.ArgumentParser()
parser.add_argument("--server-ip-addr", default="0.0.0.0", help="IP address of server")
parser.add_argument("--server-port", default=8319, type=int, help="Port of server")

args = parser.parse_args()

class UDPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        request = self.request[0]
        client_socket = self.request[1]

        Sr = int.from_bytes(request[:4], "big")
        Pr = int.from_bytes(request[4:8], "big")

        addr = "{0}:{1}".format(*self.client_address)

        logging.debug(f"{addr}:Request Sr={Sr} Pr={Pr}")

        msg_id = random.randint(0, 1 << 31)
        msg = bytes([random.randint(0x00, 0xFF) for _ in range(random.randint(4, 20))])
        reply = int.to_bytes(Pr, 4, "big") + int.to_bytes(msg_id, 4, "big") + msg

        logging.debug(f"{addr}:Reply Pr={Pr} msg_id={msg_id} msg_len={len(msg)}")
        client_socket.sendto(reply, self.client_address)


logging.basicConfig(level=logging.DEBUG)

server = socketserver.UDPServer((args.server_ip_addr, args.server_port), UDPRequestHandler)
logging.info(f"Started host on {args.server_ip_addr}:{args.server_port}")
try:
    server.serve_forever()
except KeyboardInterrupt:
    server.shutdown()
    server.server_close()
#Sends socket requests to server backdoor and sends packets to snoop middle man
#Socketserver is used to receive Sr from RealSnooperServer
# Uses UDP
import socket,socketserver

class UDPRequestHandler(socketserver.BaseRequestHandler):

    def handle(self):
        SERVER_IP_ADDR = "149.171.36.192"
        SERVER_PORT = 8319
        request = self.request[0]
        client_socket = self.request[1]
        print("request:",request)
        received = 0
        received = received.to_bytes(4,byteorder="big")
        self.server.sock_1.sendto(request, (SERVER_IP_ADDR, SERVER_PORT))
        try:
            received = self.server.sock_1.recv(1024)
            received = self.server.sock_1.recv(1024)
        except socket.timeout:
            print('Timeout')
            
        client_socket.sendto(received,self.client_address)


if __name__ == "__main__":
    #This server address & port
    HOST,PORT = "localhost",8889

    try:
        #Set up Server
        server = socketserver.UDPServer((HOST, PORT), UDPRequestHandler)
        #Set up Socket
        server.sock_1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server.sock_1.settimeout(2)
        #Start Server
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        server.server_close()
        



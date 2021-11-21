#Sends socket requests to server backdoor and sends packets to snoop middle man
#Socketserver is used to receive Sr from RealSnooperServer
# Uses UDP
# Need to update using only sockets
import socket


def handle(s,sock,datagram,addr):
    SERVER_IP_ADDR = "149.171.36.192"
    SERVER_PORT = 8319
    request = datagram
    print("request:",request)
    received = 0
    received = received.to_bytes(4,byteorder="big")

    Pr = int(request[4:8].hex(), 16)
    Pt = -1
    print(f"Pr:{Pr}\n")
    sock.sendto(request, (SERVER_IP_ADDR, SERVER_PORT))
    MAXTRY = 5
    tries =0
    while tries <MAXTRY and Pr != Pt:
        try:
            received = sock.recv(1024)
            received = sock.recv(1024)
        except socket.timeout:
            print('Timeout')
            break
        Pt = int(received[:4].hex(), 16)
        print(f"Pt:{Pt}")

        if Pr == Pt:
            print("Match!")
        tries += 1
        if tries == MAXTRY:
            print("MAXTRIES EXCEEDED!")
    Pt = int(received[:4].hex(), 16)
    print(f"Responding Pr:{Pt}")
    s.sendto(received,addr)


if __name__ == "__main__":
    #This server address & port
    HOST_SERV,PORT_SERV = "localhost",8889

    sock= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Socket thats connects to Snoop-Me Server
    sock.settimeout(0.5)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)     #Socket that listens for requests from solver
    s.bind((HOST_SERV, PORT_SERV))
        
    while True:
        try:
            datagram,addr = s.recvfrom(1024)
        except KeyboardInterrupt:
            sock.close()
            s.close()
            break
        handle(s,sock,datagram,addr)
    print("Closing Snoop Feeder 1 Server")
    
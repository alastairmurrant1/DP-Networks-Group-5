import socket


if __name__ == '__main__':
    HOST = []
    PORT = []
    #HOST.append('34.87.197.254') 
    HOST.append("localhost") 
    PORT.append(8889)
    #Snoop Feeder 2
    #HOST.append('34.116.69.217')
    HOST.append("localhost") 
    PORT.append(8920) 

    socks = []
    for _ in range(2):
        sock= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.5)
        socks.append(sock)
    for i in range(2):
        try:
            socks[i].sendto(b'',(HOST[i],PORT[i]))
        except socks[i].timeout:
            print("Timeout")
    
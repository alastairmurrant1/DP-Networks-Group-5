# Echo server program
import socket
import time

#Snoop Feeder 1 connects directly to the Snoop Server
def toSnoopFeeder(data,sock,HOST,PORT):
    print(f"data:{data} HOST:{HOST} PORT:{PORT}")
    sock.sendto(data, (HOST, PORT))
    received = 0
    received = received.to_bytes(4,byteorder="big")
    try:
        if HOST == "149.171.36.192":
            received = sock.recv(1024)
            received = sock.recv(1024)
        else:
            received = sock.recv(1024)
            print("Snooper Feeder !!")

    except socket.timeout:
        print('Timeout')

    print(received)
    if received == 0:
        len_rec = 0
    else:
        len_rec = len(received)
        print(len_rec)
    return (len_rec,received)

def decode_response(data):
    data1 = data[:8]
    data2 = data[8:16]
    data3 = data[16:]
    
    return (data1,data2,data3)

if __name__ == "__main__":

    datagram_length = 24 #24 Bytes
    num_feeders = 3
    #Server Host
    HOST_SERV = 'localhost'                 
    PORT_SERV = 33434  

    HOST = []
    PORT = []            
    #Snoop-Me Server
    HOST.append("149.171.36.192") 
    PORT.append(8319) 
    #Snoop Feeder 1
    HOST.append('localhost') 
    PORT.append(8889)
    #Snoop Feeder 2
    HOST.append('localhost')
    PORT.append(8920) 

    #Sockets used to connect to snoop feeders, in case of SF1 connects directly to server
    sock= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2)
 

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((HOST_SERV, PORT_SERV))
        i = 0
        try:
            while True:
                datagrams,addr = s.recvfrom(1024)
                print("datagrams:",datagrams)
                data = [None,None,None]
                data[0],data[1],data[2] = decode_response(datagrams)
                print("data:",data)
                len_res= []
                com_res = b''
                if len(datagrams) == datagram_length:
                    for i in range(num_feeders):
                        length_res,response = toSnoopFeeder(data[i],sock,HOST[i],PORT[i])
                        com_res += response
                        len_res.append(length_res.to_bytes(4,"big"))
                    print("len_res",len_res[0])
                    com_res = len_res[0] + len_res[1] + len_res[2]+ com_res
                    
                    print(f"Final Response {com_res}")
                    s.sendto(com_res,addr)
                    print("i:",i)
                    i+=1
                else: 
                    raise ValueError("Datagram Dimensions Incorrect!")

        except KeyboardInterrupt:
            print("reached")
            sock.close()
            s.close()
            exit()
    

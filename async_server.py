# Echo server program
import socket
import concurrent.futures

#Snoop Feeder 1 connects directly to the Snoop Server
def toSnoopFeeder(data,sock,HOST,PORT):
    print(f"data:{data} HOST:{HOST} PORT:{PORT}")
    sock.sendto(data, (HOST, PORT))
    received = 0
    received = received.to_bytes(4,byteorder="big")
    if HOST == "149.171.36.192":
        Pr = int(data[4:8].hex(), 16)
        Pt = -1
      
        MAXTRY = 5
        tries =0
        while tries <MAXTRY and Pr != Pt and Pt != 0:
            try:
                received = sock.recv(1024)
                received = sock.recv(1024)
            except socket.timeout:
                print('Timeout')
            Pt = int(received[:4].hex(), 16)
            print(f"Pt:{Pt}")

            if Pr == Pt:
                print("Match!")
            tries += 1
            if tries == MAXTRY:
                print("MAXTRIES EXCEEDED!")
    else:
        try:
            received = sock.recv(1024)
        except socket.timeout:
            print("Timeout")

    
    if received == 0:
        len_rec = 0
    else:
        len_rec = len(received)
        #print(len_rec)
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
    requests_serviced = 0
    HOST = []
    PORT = []            
    #Snoop-Me Server
    HOST.append("149.171.36.192") 
    PORT.append(8319) 
    #Snoop Feeder 1
    #HOST.append('34.87.197.254') 
    HOST.append("localhost") 
    PORT.append(8889)
    #Snoop Feeder 2
    #HOST.append('34.116.69.217')
    HOST.append("localhost") 
    PORT.append(8920) 

    #Sockets used to connect to snoop feeders, in case of SF1 connects directly to server
    socks = []
    for i in range(num_feeders): 
        sock= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        socks.append(sock)
    
 

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((HOST_SERV, PORT_SERV))
        try:
            while True:
                datagrams,addr = s.recvfrom(1024)

                #print("datagrams:",datagrams)
                data = [None,None,None]
                data[0],data[1],data[2] = decode_response(datagrams)
                #print("data:",data)
                len_res= []
                com_res = b''
                if len(datagrams) == datagram_length:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                        str = []
                        print(f"Starting Workers")
                        future_feeder = {executor.submit(toSnoopFeeder,data[i],socks[i],HOST[i],PORT[i]): i for i in range(3)}
                        concurrent.futures.wait(future_feeder)
                        for future in concurrent.futures.as_completed(future_feeder):
                            length_res,response = future.result()
                            test_Pr = int.from_bytes(response[:4],"big")
                            sent_Pr = int.from_bytes(data[future_feeder[future]][4:8],"big")
            
                            print(f"Finished Worker{future_feeder[future]} Pr Received: {test_Pr}  Pr Sent: {sent_Pr}")
                            com_res += response
                            len_res.append(length_res.to_bytes(4,"big"))

                    com_res = len_res[0] + len_res[1] + len_res[2]+ com_res
                    
                    #print(f"Final Response {com_res}")
                    requests_serviced += 1
                    print(f"Requests Serviced {requests_serviced}\n ")
                    s.sendto(com_res,addr)

                else: 
                    raise ValueError("Datagram Dimensions Incorrect!")

        except KeyboardInterrupt:
            print("reached")
            for sock in socks:
                sock.close()
            s.close()
    

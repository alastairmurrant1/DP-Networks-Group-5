# Implementation by turning it into an real server, to allow greater cohesion with 
# Snooper algorithm
# Add threading in order to implement exposure and inaccurate packet sniping due to delays.
# Queueing ?

import socketserver,time
import http.server
import threading
import random
from sys import byteorder
import queue    

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)       # Don't know how to send proper HTTP status response
        

class ThreadingServer(socketserver.ThreadingMixIn,http.server.HTTPServer):
    pass

class ThreadedUDPRequestHandler(socketserver.BaseRequestHandler):

    

    def handle(self):
        socket = self.request[1]
        request = self.request[0]

        Sr = request[:4]
        Pr = request[4:]
        Sr_int = int.from_bytes(Sr,byteorder="big")

        #prevID = self.server.msg_id
        #nextID = (self.server.msg_id + Sr_int)%(1 << 63)

        if self.client_address[1] not in self.server.unique_client:
            if len(self.server.unique_client) >= 3:
                self.server.handle_error(self.request,self.client_address)
                
            else:
                self.server.unique_client.append(self.client_address[1])
                client_index = self.server.unique_client.index(self.client_address[1])+1
                queue_len = 2
                self.server.dict_ID[client_index] = [-1,-1,Sr_int,Pr,queue_len]

        else:
            client_index = self.server.unique_client.index(self.client_address[1])+1
            self.server.dict_ID[client_index][2:4] = [Sr_int,Pr]
        
        self.server.dict_ID[client_index][0] = self.server.dict_ID[client_index][1]
        self.server.dict_ID[client_index][1] = self.server.msg_id


        while self.server.dict_ID[client_index][2] > 0:

            pass

        self.server.dict_ID[client_index][0] = self.server.dict_ID[client_index][1]
        self.server.dict_ID[client_index][1] = self.server.msg_id
               
        while self.server.dict_ID[client_index][4] == 0:        #Blocks until queue length != 0
            pass


        msg = server.packets[self.server.packet_num]
        Pr_int = int.from_bytes(Pr,"big")
        print(f"Pr:{Pr_int} Sr:{Sr_int} Msg:{msg}")
        print(self.client_address[1])
        datagram = Pr + self.server.msg_id.to_bytes(4,byteorder="big") + msg
        socket.sendto(datagram,self.client_address)

class ThreadedUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):    
    pass

def check_inter_response(server,key):
        inter_response_threshold = 50
        inter_response_rate = 0
        prevID = server.dict_ID[key][0]
        nextID  = server.dict_ID[key][1]

        for i in range(prevID, nextID):
            i = i % len(server.packets)
            inter_response_rate += len(server.packets[i])
        
        # If inter-response rate too low, reduce snooper queue
        if inter_response_rate < inter_response_threshold:
            print("Inter response too low")
            server.dict_ID[key][4] = max(0, server.dict_ID[key][4]-1)
            if server.dict_ID[key][4] == 0:
                print("Snooper detected")

def MainThread(server):
    i = 0
    inter_response_queue_increment = 1000
    
    check_response = []
    main_thread = threading.current_thread()
    while getattr(main_thread,"do_run",True): 
        sleep_t = len(server.packets[server.packet_num])*(1/server.data_rate )*(1/100000)
        time.sleep(sleep_t)
        #print("sleep time= ",sleep_t,"packet length=",len(server.packets[server.packet_num]))
        server.msg_id = (server.msg_id + 1)%(1<<63)
        server.packet_num  = (server.packet_num + 1)%(len(server.packets))
        
        for key in server.dict_ID:
            if server.dict_ID[key][2] !=-1:
                server.dict_ID[key][2] -= 1
                if server.dict_ID[key][2] == 0:
                    check_response.append(key)
                    server.dict_ID[key][2] = -1
                    #server.inter_response_buffer[key] = 0

            server.inter_response_buffer[key] += len(server.packets[server.packet_num])
            if server.inter_response_buffer[key] > inter_response_queue_increment:
                server.dict_ID[key][4] = min(2, server.dict_ID[key][4]+1)
                server.inter_response_buffer[key] = 0
        
                
        for key in check_response:
            if server.dict_ID[key][0] == -1:
                pass
            else:
                print("key = ",key)
                check_inter_response(server,key)
        check_response = []

    print("Killing Main Thread")

if __name__ == "__main__":
    HOST,PORT = "localhost", 9999
    AUTH_PORT = PORT  - 1
    data_rate = 1000                # data_rate*chars/second
    txt_msg ="testcase2.txt"

    server = ThreadedUDPServer((HOST, PORT), ThreadedUDPRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server.daemon = True
    server_runtime = 180 # in seconds

    
    httpd= ThreadingServer((HOST,AUTH_PORT),Handler)
    httpd_thread = threading.Thread(target=httpd.serve_forever)
    httpd.daemon = True

    try:
        server_thread.start()
        print("Server started at {} port {}".format(HOST, PORT))
        httpd_thread.start()
        print("HTTP started at {} port {}".format(HOST,AUTH_PORT))
        with open(txt_msg) as fp:
                server.data = fp.read()
                server.data_rate = data_rate
                server.packet_num = 0
                server.packets = []
                server.msg_id = random.randint(0,1<<16)
                server.msg = bytes(server.data + chr(0x04),"utf-8")
                server.queue_len = 2
                server.unique_client = []   # Keeps track of unique clients, can be altered to track IP's as well
                server.dict_ID = {1:[-1,-1,-1,-1,-1],     # :prevID,nextID,Sr,Pr,Queue Length
                                2:[-1,-1,-1,-1,-1],
                                3:[-1,-1,-1,-1,-1]}     
                server.inter_response_buffer = {1:0, 2:0,3:0}       # Usings unique client num to keep track of previous msgIDs for inter response checks

                N = len(server.msg)
                i = 0
                while i < N:
                    msg_len = random.randint(4, 20)
                    msg_packet =server.msg[i:i+msg_len]
                    server.packets.append(msg_packet)
                    i += msg_len
        
        main_thread = threading.Thread(target=MainThread,args= (server,),daemon=True) 
                 
        main_thread.start()
        time.sleep(server_runtime)
        print("Sleep Over")
        main_thread.do_run = False
        main_thread.join()
        server.shutdown()

        server.server_close()
        exit()
      
    except (KeyboardInterrupt, SystemExit):
        server.shutdown()
        httpd.shutdown()
        server.server_close()
        httpd.server_close()
        exit()
   

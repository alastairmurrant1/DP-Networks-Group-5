import socket,random,struct

HOST,PORT = "localhost",33434
Pr1 = random.randint(1, 1 << 31)
Sr1 = 14
Pr2 = random.randint(1, 1 << 31)
Sr2 = 11
Pr3 = random.randint(1, 1 << 31)
Sr3 = 17
datagram = struct.pack(">LLLLLL", Sr1, Pr1,Sr2,Pr2,Sr3,Pr3)
# SOCK_DGRAM is the socket type to use for UDP sockets
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(3)

sock.sendto(datagram, (HOST, PORT))
try:
    received = sock.recv(1024)
except socket.timeout:
    print('Timeout')

snoopers = 3
msg = []
Pt = []
msg_id = []
length_res = []
length_res.append(int.from_bytes(received[:4],"big"))
length_res.append(int.from_bytes(received[4:8],"big"))
length_res.append(int.from_bytes(received[4:12],"big"))

#length_res.append(received[4:8])
start_len = snoopers*4
for i in range(snoopers):
    Pt = int.from_bytes(received[start_len:start_len+4],"big")
    msg_id = int.from_bytes(received[start_len+4:start_len+8],"big")
    msg = received[start_len+8:start_len+length_res[i]]

    msg = str(msg, 'ascii').replace('\n', '')
    if i == 1:
        print(f"Pr: {Pt} {Pr2} MsgID: {msg_id} Length: {length_res[i]} Message: {msg}")
    elif i == 2:
        print(f"Pr: {Pt} {Pr3} MsgID: {msg_id} Length: {length_res[i]} Message: {msg}")

    else:
        print(f"Pr: {Pt} {Pr1} MsgID: {msg_id} Length: {length_res[i]} Message: {msg}")

    start_len = start_len + length_res[i]
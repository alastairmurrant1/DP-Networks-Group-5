# %%
import socket

SERVER_IP_ADDR = "149.171.36.192"
SERVER_PORT = 8319
SERVER_AUTH_PORT = SERVER_PORT+1

# Create our http post request
def construct_post_request(message, version="1.1", headers={}):
    request = ""
    request += f"POST / HTTP/{version}\r\n"
    request += f"Host: {SERVER_IP_ADDR}:{SERVER_AUTH_PORT}\r\n"
    
    for k, v in headers.items():
        request += f"{k}: {v}\r\n"
    
    msg_len = len(message)
    
    request += f"Content-Length: {msg_len}\r\n"
    request += "\r\n" + message
    
    return request

# Decode our http post response
# Return the status code
def decode_post_response(res):
    res = str(res, "utf-8")
    lines = res.split("\n")
    header = lines[0].split(' ')
    status_code = int(header[1])
    return status_code

# Create a tcp socket and send our http post request
# Returns the status code if successful, None if timed out
def send_post_request(message, headers={}, ip_addr=SERVER_IP_ADDR, port=SERVER_AUTH_PORT):
    # create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    sock.connect((ip_addr, port))

    request = construct_post_request(message, headers=headers)
    n = sock.send(bytes(request, "utf-8"))
    
    try:
        data = sock.recv(1024)
        res = decode_post_response(data)
        return res
    except socket.timeout:
        return None
    finally:
        sock.close()

# %% Example of post request
headers = {"Connection": "close"} # close the tcp connection when done
message = "hello world" + chr(0x04)
res = send_post_request(message, headers=headers)
print(res)    

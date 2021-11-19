from create_snooper_feeder import create_snooper_feeder
import logging

#This server address & port
HOST,PORT = "0.0.0.0",8889
logging.basicConfig(level=logging.DEBUG)

try:
    #Set up Server
    server = create_snooper_feeder(HOST, PORT)
    server.serve_forever()
except KeyboardInterrupt:
    server.shutdown()
    server.server_close()
        



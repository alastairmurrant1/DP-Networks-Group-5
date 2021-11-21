from create_snooper_feeder import create_snooper_feeder
import logging

#This server address & port
HOST,PORT = "0.0.0.0",8921
logging.basicConfig(level=logging.DEBUG)

server = create_snooper_feeder(HOST, PORT)
server.run()
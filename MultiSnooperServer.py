import socket
import random
import logging

"""
Connects to the local snooper server which communicates with its 3 child servers
"""
class MultiSnooperServer:
    def __init__(self, snoopers, logger=None):
        self.snoopers = snoopers
        self.logger = logger or logging.getLogger(__name__)
    
    @property
    def TOTAL_SNOOPERS(self):
        return len(self.snoopers)

    # Returns an array of packets
    # A packet is None is that snooping channel has timedout 
    # A packet is defined if that snooping channel replied back
    def get_messages(self, Sr_arr, Pr_arr=None):
        assert len(Sr_arr) == self.TOTAL_SNOOPERS
        if Pr_arr is None:
            Pr_arr = [random.randint(1, 1 << 31) for _ in range(self.TOTAL_SNOOPERS)]
        
        packets = list(zip(Sr_arr, Pr_arr))
        
        # create callbacks
        callbacks = []
        for i, ((Sr, Pr), snooper) in enumerate(zip(packets, self.snoopers)):
            callback = snooper.get_message(Sr, Pr, return_callback=True)
            callbacks.append(callback)

        # use callback after all datagrams sent
        responses = []
        for i, callback in enumerate(callbacks):
            try:
                msg_id, msg = callback()
                responses.append((msg_id, msg))
            except socket.timeout:
                self.logger.warn(f"Got timeout from snooper#{i}")
                responses.append(None)
        
        return responses
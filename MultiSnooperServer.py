import socket
import concurrent.futures
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
    
    def attempt_snoop(self, snooper, Sr, Pr, index):
        try:
            return snooper.get_message(Sr, Pr, return_callback=False)
        except socket.timeout:
            self.logger.warn(f"Got timeout from snooper#{index}")
            return None

    # Returns an array of packets
    # A packet is None is that snooping channel has timedout 
    # A packet is defined if that snooping channel replied back
    def get_messages(self, Sr_arr, Pr_arr=None):
        assert len(Sr_arr) == self.TOTAL_SNOOPERS
        if Pr_arr is None:
            Pr_arr = [random.randint(1, 1 << 31) for _ in range(self.TOTAL_SNOOPERS)]
        
        packets = list(zip(Sr_arr, Pr_arr))

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.TOTAL_SNOOPERS) as executor:
            promises = []
            for i, ((Sr, Pr), snooper) in enumerate(zip(packets, self.snoopers)):
                promise = executor.submit(self.attempt_snoop, snooper, Sr, Pr, i)
                promises.append(promise)

            responses = [] 
            for future in concurrent.futures.as_completed(promises):
                responses.append(future.result())

        return responses
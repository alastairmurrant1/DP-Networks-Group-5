from functools import reduce
import random
import socket

# https://stackoverflow.com/questions/6800193/what-is-the-most-efficient-way-of-finding-all-the-factors-of-a-number-in-python
def factors(n):    
    return set(reduce(list.__add__, ([i, n//i] for i in range(1, int(n**0.5) + 1) if n % i == 0)))

class Solver_V1:
    def __init__(self, snooper, flush=True):
        self.snooper = snooper
        self.total_requests = 0

        self.all_packets = []
        self.EOF_packets = []
        self.unique_packets = set([])

        # store all the potential messages
        # key = length of potential message
        # value = [packet] array of message parts as bytes
        self.possible_messages = {}
        
        # keep track of important message ids 
        self.STARTER_ID = None
        self.LAST_ID = None
        
        # total maximum based on spec
        # maximum input length is 5000
        # minimum packet length is 4
        # therefore this is our maximum number of packets
        self.MAX_PACKETS = (5000//4) + 1
        self.MAX_RETRIES = 10
        
        self.flush = flush
        
        self.PRINT_DEBUG = False
        self.PRINT_INFO = True

        # keep track of sniping attempts
        self.snipe_attempts = 0
        self.snipe_success = 0
        self.snipe_errors = []

        # if there is a consistent delay in our sniping, calibrate for this
        self.SNIPE_OFFSET = 0
        
    def print_debug(self, msg):
        if self.PRINT_DEBUG:
            print(msg)
            
    def print_info(self, msg):
        if self.PRINT_INFO:
            print(msg)
        
    # greedy search the best Cr to snipe a packet
    def get_Cr(self):
        # random search if cant snipe
        if not self.possible_messages.keys() or not self.LAST_ID:
            return random.randint(8,12)
        
        # greedy snipe
        hop_scores = []
        for hop in range(7, 100):
            score = 0
            for N, chunks in self.possible_messages.items():
                i = self.get_relative_index(self.LAST_ID+hop, N)
                if chunks[i] is None:
                    score += 1
            sort_val = (score << 10) - abs(hop-10)
            hop_scores.append((sort_val, score, hop))
        
        _, best_score, best_hop = max(hop_scores, key=lambda h:h[0])
        
        self.print_debug(f"[DEBUG] Sniping for {self.LAST_ID+best_hop} with hop={best_hop} score={best_score}")
        return best_hop
        
    
    # get message and add them to the relevant queues
    def get_message(self, Cr=None):
        if Cr is None:
            Cr = self.get_Cr()
        
        for _ in range(self.MAX_RETRIES):
            try:
                packet = self.snooper.get_message(Cr-self.SNIPE_OFFSET)
                self.total_requests += 1
                break
            except socket.timeout:
                self.print_debug(f"[DEBUG] Got a timeout @ {self.total_requests}")
                continue
        else:
            raise Exception(f"Timed out after {self.MAX_RETRIES} retries")
                
        msg_id, msg = packet

        # check if our packet sniping was successful
        if self.LAST_ID is None:
            snipe_success = None
        else:
            target_id = self.LAST_ID+Cr 
            snipe_success = target_id == msg_id
            self.snipe_attempts += 1
            self.snipe_success += int(snipe_success)
            self.snipe_errors.append(target_id-msg_id)

        # keep track of last id for future sniping attempts
        self.LAST_ID = msg_id

        self.print_debug(f"[DEBUG] Got [{msg_id}] @ {self.total_requests} snipe_success=[{snipe_success}]")

        # add packet to relevant queues        
        self.all_packets.append(packet)

        if 0x04 in msg:
            self.EOF_packets.append(packet)
        
        self.unique_packets.add(msg)
        return packet
    
    # get our initial possibLe_messages set
    # possible_messages = {}
    # key = possible_length 
    # value = [array of substrings]
    # substring = None if not found yet
    def get_initial_estimates(self):
        # flush old responses
        if self.flush:
            for _ in range(10):
                self.get_message()
                
        # reset packet queues
        self.all_packets = []
        self.EOF_packets = []
        self.unique_packets = set([])
        
        # get maximum possible length
        while True:
            packet = self.get_message()
            if len(self.EOF_packets) >= 2:
                break
    
        # get possible message length in terms of total number of packets
        (eof_id_1, _), (eof_id_2, _) = self.EOF_packets[:2]
        N = eof_id_2-eof_id_1
        possible_lengths = factors(N)
        self.STARTER_ID = eof_id_1 + 1 # a known starting index
        
        self.print_debug(f"[DEBUG] Possible lengths {possible_lengths}")
        
        # create blank chunks list for each possible length
        self.possible_messages = {}
        for N in possible_lengths:
            chunks = [None] * N        
            self.possible_messages[N] = chunks
            
        # seed our initial message list
        self.construct_messages()
        self.cull_invalid_lengths()
        
    # cull the possible lengths based on 
    # the minimum possible length based on number of non-duplicate packets recieved
    def cull_invalid_lengths(self):  
        nb_unique_packets = len(self.unique_packets)
        for N in list(self.possible_messages.keys()):
            if N < nb_unique_packets or N > self.MAX_PACKETS:
                self.print_debug(f"[DEBUG] Removed length {N} since outside of lower and upper bound")
                self.possible_messages.pop(N, None)
    
    # get the index inside the partially complete message
    def get_relative_index(self, msg_id, length):
        return (msg_id - self.STARTER_ID) % length
    
    # if there are unprocessed packets, add them to the possible messages
    def construct_messages(self):
        self.cull_invalid_lengths()
        
        invalid_lengths = set([])
        for N, chunks in self.possible_messages.items():
            for msg_id, msg in self.all_packets:
                i = self.get_relative_index(msg_id, N)
                chunk = chunks[i]

                # if message contains terminator character but is not at the end of the possible message
                if 0x04 in msg and i != (N-1):
                    invalid_lengths.add(N)
                    break
                    
                # check if a conflict exists, if it does then this is not a possible length
                if chunk is not None and chunk != msg:
                    invalid_lengths.add(N)
                    break
                
                # insert our packet
                if chunk is None:
                    chunks[i] = msg
        
        # processed all packets
        self.all_packets = []
        
        # cull invalid messages
        for N in invalid_lengths:
            self.print_debug(f"[DEBUG] Removed length {N} since message conflicts when wrapping")
            self.possible_messages.pop(N, None)
            
    # check if there are completed messages
    def check_completed_messages(self):
        nb_possible = len(self.possible_messages.keys())
        if nb_possible == 0:
            raise ValueError("No possible messages")
        
        completed_messages = {}
        for N, chunks in self.possible_messages.items():
            if None not in chunks:
                completed_messages[N] = chunks

        nb_completed = len(completed_messages.keys())
        if nb_completed == 0:
            return None
        
        # if for some reason we got a "completed" message with a single packet
        # this could mean we got a single packet message
        # or we were unlucky and only got the delimiter packet twice in a row 
        # we only take this as the "completed" message if there are no other possibilities
        if nb_completed == 1 and nb_possible > 1 and completed_messages.get(1, False):
            self.print_debug("[DEBUG] Ignoring 'completed' single packet message")
            return None

        
        self.possible_messages = completed_messages
        
        progress = {k:sum((c is not None for c in v)) for k, v in self.possible_messages.items()}
        self.print_info(f"[INFO] Completed {progress} @ {self.total_requests}")
        
        if nb_completed > 1:
            print(f"[WARN] Got multiple completed messages: {list(completed_messages.keys())}")
            
        final_msg = list(completed_messages.values())[0]
        final_msg = ''.join((str(chunk, "utf-8") for chunk in final_msg))[:-1]
        return final_msg
        
    def run(self):
        self.print_debug(f"[DEBUG] Starting solver run")
        self.get_initial_estimates()
        
        while True:
            final_msg = self.check_completed_messages()
            if final_msg is not None:
                return final_msg
            
            progress = {k:sum((c is not None for c in v)) for k, v in self.possible_messages.items()}
            self.print_debug(f"[DEBUG] Progress {progress} @ {self.total_requests}")
            
            self.get_message()
                
            self.construct_messages()
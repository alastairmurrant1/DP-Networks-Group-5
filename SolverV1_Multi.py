import random
import socket
import logging

# https://stackoverflow.com/questions/6800193/what-is-the-most-efficient-way-of-finding-all-the-factors-of-a-number-in-python
from functools import reduce
def factors(n):    
    return set(reduce(list.__add__, ([i, n//i] for i in range(1, int(n**0.5) + 1) if n % i == 0)))

from PossibleMessage import PossibleMessage, ChunkConflict, EOFMismatch

class Solver_V1_Multi:
    def __init__(self, snooper, snipers, logger=None):
        self.snooper = snooper
        self.snipers = snipers

        # Maximum possible number of packets in potential message
        self.MAX_PACKETS = 5000//4
        # Number of retries to snooper before giving up
        self.MAX_RETRIES = 10
        # If we are using dense guessing, determine threshold before we start
        # to use greedy sniping
        self.DENSE_GUESS_THRESHOLD = 100

        self.logger = logger or logging.getLogger(__name__)
        
        
        self.total_requests = 0
        self.all_packets = []
        self.unique_packets = set([])
        self.EOF_packets = []
        self.EOF_ids = set([])
        
        # use starter id to get message offset
        self.STARTER_ID = None
        self.LAST_ID = None
        self.FOUND_FACTORS = False
        
        # store all the potential messages
        # key = length of potential message
        # value = PossibleMessage object
        self.possible_messages = set([])
    
    @property
    def TOTAL_SNOOPERS(self):
        return self.snooper.TOTAL_SNOOPERS
    
    # get score if we attempt to snipe a particular location
    # we know the probability of an offset occuring
    def get_sniping_score(self, target_id, snooper_index):
        index = target_id-self.STARTER_ID
        sniper = self.snipers[snooper_index]
        return sniper.get_score(self.possible_messages, index)
    
    # get the actual score
    def get_actual_score(self, target_id):
        score = 0
        for message in self.possible_messages:
            i = target_id-self.STARTER_ID
            if message[i] is None:
                score += 1
        return score
        
    # greedy search the best Cr to snipe a packet
    def get_Crs(self):
        # random search if cant snipe
        if not self.LAST_ID:
            return [random.randint(11,20) for _ in range(self.TOTAL_SNOOPERS)]

        if self.FOUND_FACTORS or len(self.possible_messages) < self.DENSE_GUESS_THRESHOLD:
            return [self.greedy_snipe(i) for i in range(self.TOTAL_SNOOPERS)]
        
        return [random.randint(11,20) for _ in range(self.TOTAL_SNOOPERS)]

    def greedy_snipe(self, snooper_index): 
        hop_scores = []
        for hop in range(7,100):
            score = self.get_sniping_score(self.LAST_ID+hop, snooper_index)
            sort_val = score*1000 - abs(hop-random.randint(12,40))
            hop_scores.append((sort_val, score, hop))
        
        _, best_score, best_hop = max(hop_scores, key=lambda h:h[0])
        
        self.logger.debug(f"Sniping snooper#{snooper_index} for {self.LAST_ID+best_hop} with hop={best_hop} score={best_score:.2f}")
        return best_hop

    # calculate factors and update possible messages 
    def calculate_factors(self):
        if len(self.EOF_packets) < 2:
            return
        
        self.logger.debug(f"Calculating factors")        
        self.FOUND_FACTORS = True

        ids = [id for id,_ in self.EOF_packets]

        # find the possible combination of lengths from EOF characters
        lengths = [] 
        for i in range(len(ids)-1):
            start_id = ids[i]
            end_ids = ids[i+1:]
            for end_id in end_ids:
                lengths.append(end_id-start_id)

        lengths = set.intersection(*[set(factors(n)) for n in lengths])

        invalid_messages = []
        for m in self.possible_messages:
            if len(m) not in lengths:
                invalid_messages.append(m)

        for m in invalid_messages:
            self.logger.debug(f"Removed length {len(m)} since not a factor")        
            self.possible_messages.remove(m)
    
    # get message and add them to the relevant queues
    def get_message(self, Crs=None):
        if Crs is None:
            Crs = self.get_Crs()
        
        # attempt to get message
        for _ in range(self.MAX_RETRIES):
            try:
                packets = self.snooper.get_messages(Crs)
                self.total_requests += 1
                break
            except socket.timeout:
                self.logger.debug(f"Got a timeout @ {self.total_requests}")
                continue
        else:
            raise Exception(f"Timed out after {self.MAX_RETRIES} retries")
        
        # add packets to relevant queues
        for i, packet in enumerate(packets):
            if packet is None:
                self.logger.debug(f"socket#{i} timedout")
                continue

            msg_id, msg = packet
            self.all_packets.append(packet)
            self.unique_packets.add(msg)

        # insert the EOF packets in sorted order 
        for packet in sorted(filter(None, packets)):
            msg_id, msg = packet
            if 0x04 in msg and msg_id not in self.EOF_ids:
                self.EOF_ids.add(msg_id)
                self.EOF_packets.append(packet)
                self.calculate_factors()
        
        # update tracker ids
        snipers = [sniper for packet, sniper in zip(packets, self.snipers) if packet]
        Crs = [Cr for packet, Cr in zip(packets, Crs) if packet]
        indices = [i for packet, i in zip(packets, range(self.TOTAL_SNOOPERS)) if packet]
        packets = [packet for packet in packets if packet]

        # if no valid packets, then all snoopers have timedout
        if len(packets) == 0:
            self.logger.error("All snooper channels have timed out")
            return

        msg_ids = [msg_id for msg_id, _ in packets]
        if self.STARTER_ID is None:
            self.STARTER_ID = min(msg_ids)

        last_id = self.LAST_ID
        self.LAST_ID = max(msg_ids)

        if last_id is None:
            return

        # determine sniping error for each snooper
        sniper_errors = []
        for sniper, packet, Cr in zip(snipers, packets, Crs):
            msg_id, _ = packet
            target_id = last_id+Cr
            error = msg_id-target_id
            sniper.push_error(msg_id-target_id)
            sniper_errors.append(error)

        # for each packet, get its actual score
        scores = [self.get_actual_score(msg_id) for msg_id in msg_ids]

        # keep track of last id for future sniping attempts
        metadata = zip(indices, msg_ids, scores, sniper_errors)
        for i, msg_id, score, sniper_error in metadata:
            self.logger.debug(f"Got [{msg_id}] @ {self.total_requests} snooper={i} snipe_error=[{sniper_error}] score=[{score}]")
        
        return packet
        
    # cull the possible lengths based on 
    # the minimum possible length based on number of non-duplicate packets recieved
    def cull_invalid_lengths(self):  
        nb_unique_packets = len(self.unique_packets)
        for message in list(self.possible_messages):
            N = len(message)
            if N < nb_unique_packets:
                self.logger.debug(f"Removed length {len(message)} since below min_unique={nb_unique_packets}")
                self.possible_messages.remove(message)
        
    # if there are unprocessed packets, add them to the possible messages
    def construct_messages(self):
        for message in list(self.possible_messages):
            for chunk_id, chunk in self.all_packets:
                i = chunk_id-self.STARTER_ID
                try:
                    message[i] = chunk
                except ChunkConflict:
                    self.possible_messages.remove(message)
                    self.logger.debug(f"Removed length {len(message)} due to chunk conflict")        
                    break
                except EOFMismatch:
                    self.possible_messages.remove(message)
                    self.logger.debug(f"Removed length {len(message)} due to EOF mismatch")        
                    break

    # check if there are completed messages
    def check_completed_messages(self):
        if len(self.possible_messages) == 0:
            raise ValueError("No possible messages")
            
        # ignore if there is another potential match    
        if len(self.possible_messages) > 1:
            return None
        
        completed_messages = [m for m in self.possible_messages if m.is_complete]
        if len(completed_messages) == 0:
            return None
        
        completed_message = completed_messages[0]
        return completed_message.message

    # get initial guesses from factors of maximum possible length 
    def get_initial_guess(self):
        while len(self.EOF_packets) < 2:
            self.get_message()
        
        (start_id,_), (end_id,_) = self.EOF_packets[:2]
        lengths = factors(end_id-start_id)
        lengths = [n for n in lengths if n <= self.MAX_PACKETS]
        for n in lengths:
            self.possible_messages.add(PossibleMessage(n))

        self.cull_invalid_lengths()
        self.construct_messages()

    # get all possible guesses from 1 to MAX_PACKETS 
    def get_all_guesses(self):
        for n in range(1, self.MAX_PACKETS+1):
            self.possible_messages.add(PossibleMessage(n))

    # return progress of each message as dictionary of
    # {k:v} where k=length, v=#chunks
    @property
    def progress(self):
        return {len(m):m.completed_chunks for m in self.possible_messages}
        
    def run(self, sparse_guess=True):
        self.logger.debug(f"Starting solver run")

        if sparse_guess:
            self.logger.info("Starting sparse guess from 2 EOFs")
            self.get_initial_guess()
            self.logger.info(f"Got initial guess: {[len(m) for m in self.possible_messages]}")
        else:
            self.logger.info(f"Starting dense guesses from 1 to {self.MAX_PACKETS}")
            self.get_all_guesses()

        while True:
            final_msg = self.check_completed_messages()
            if final_msg is not None:
                return final_msg
            
            if len(self.possible_messages) < 15:
                self.logger.debug(f"Progress {self.progress} @ {self.total_requests}")
                
            self.get_message()
            self.cull_invalid_lengths()
            self.construct_messages()
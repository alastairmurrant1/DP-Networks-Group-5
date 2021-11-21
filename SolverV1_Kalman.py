import random
import socket
import logging
from timeit import default_timer
from collections import deque

# https://stackoverflow.com/questions/6800193/what-is-the-most-efficient-way-of-finding-all-the-factors-of-a-number-in-python
from functools import reduce
def factors(n):    
    return set(reduce(list.__add__, ([i, n//i] for i in range(1, int(n**0.5) + 1) if n % i == 0)))

from PossibleMessage import PossibleMessage, ChunkConflict, EOFMismatch

class Solver_V1_Kalman:
    def __init__(self, snooper, sniper, rate, logger=None):
        self.snooper = snooper
        self.sniper = sniper

        # Maximum possible number of packets in potential message
        self.MAX_PACKETS = 500 # Based on probability distribution of possible total packets, highly unlikely to be above 500
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
        
        # use starter id to get message offset
        self.STARTER_ID = None
        self.LAST_ID = None
        self.FOUND_FACTORS = False

        # kalman filter
        self.pk = 0
        self.t_prev_update = 0
        self.CHAR_RATE = rate
        self.dt_prev_rx = deque([], maxlen=10)
        
        # store all the potential messages
        # key = length of potential message
        # value = PossibleMessage object
        self.possible_messages = set([])
    
    # get score if we attempt to snipe a particular location
    # we know the probability of an offset occuring
    def get_sniping_score(self, target_id):
        index = target_id-self.STARTER_ID
        return self.sniper.get_score(self.possible_messages, index)
    
    # get the actual score
    def get_actual_score(self, target_id):
        score = 0
        for message in self.possible_messages:
            i = target_id-self.STARTER_ID
            if message[i] is None:
                score += 1
        return score
        
    # greedy search the best Cr to snipe a packet
    def get_Cr(self, id):
        # random search if cant snipe
        if not self.LAST_ID:
            return random.randint(8,12)

        if self.FOUND_FACTORS or len(self.possible_messages) < self.DENSE_GUESS_THRESHOLD:
            return self.greedy_snipe(id)
        
        return random.randint(8,12)

    def greedy_snipe(self, id): 
        hop_scores = []
        for hop in range(7,20):
            score = self.get_sniping_score(id+hop)
            sort_val = score*1000 - abs(hop-10)
            hop_scores.append((sort_val, score, hop))
        
        _, best_score, best_hop = max(hop_scores, key=lambda h:h[0])
        
        # self.logger.debug(f"Sniping for {self.LAST_ID+best_hop} with hop={best_hop} score={best_score:.2f}")
        return best_hop

    # calculate factors and update possible messages 
    def calculate_factors(self):
        if len(self.EOF_packets) < 2:
            return
        
        # self.logger.debug(f"Calculating factors")        
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
            # self.logger.debug(f"Removed length {len(m)} since not a factor")        
            self.possible_messages.remove(m)

    # get message and add them to the relevant queues
    def on_message(self, msg_id, msg):
        packet = (msg_id, msg)

        # set our first packet
        if self.STARTER_ID is None:
            self.STARTER_ID = msg_id
        
        # add packet to relevant queues        
        self.all_packets.append(packet)
        self.unique_packets.add(msg)
        if 0x04 in msg:
            self.EOF_packets.append(packet)
            self.calculate_factors()
        
        self.cull_invalid_lengths()
        self.construct_messages()

        return packet
        
    # cull the possible lengths based on 
    # the minimum possible length based on number of non-duplicate packets recieved
    def cull_invalid_lengths(self):  
        nb_unique_packets = len(self.unique_packets)
        for message in list(self.possible_messages):
            N = len(message)
            if N < nb_unique_packets:
                # self.logger.debug(f"Removed length {len(message)} since below min_unique={nb_unique_packets}")
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
                    # self.logger.debug(f"Removed length {len(message)} due to chunk conflict")        
                    break
                except EOFMismatch:
                    self.possible_messages.remove(message)
                    # self.logger.debug(f"Removed length {len(message)} due to EOF mismatch")        
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

    # guess the number of packets required to fulfill character count 
    def get_known_total_chars(self, start_id, char_count, default=12):
        i = start_id - self.STARTER_ID
        message = list(self.possible_messages)[-1]
        
        total_unknown = 0
        total_known = 0
        total_char = 0

        while total_char < char_count:
            i += 1
            chunk = message[i]
            if chunk is None:
                total_char += default
                total_unknown += 1
            else:
                total_char += len(chunk)
                total_known += 1

        return (total_known, total_unknown)

    # return progress of each message as dictionary of
    # {k:v} where k=length, v=#chunks
    @property
    def progress(self):
        return {len(m):m.completed_chunks for m in self.possible_messages}
    
    # get first response to seed priors
    def seed(self):
        Sr = 10
        t0 = default_timer()
        msg_id, msg = self.snooper.get_message(Sr)
        self.total_requests += 1
        t1 = default_timer()

        rtt = t1-t0
        dt_rx = rtt - (Sr*12)/self.CHAR_RATE
        self.on_message(msg_id, msg)
        self.dt_prev_rx.append(dt_rx)

        self.LAST_ID = msg_id
        self.t_prev_update = t1

        
    def run(self):
        self.logger.debug(f"Starting solver run")
        self.logger.info(f"Starting dense guesses from 1 to {self.MAX_PACKETS}")
        self.get_all_guesses()
        self.seed()

        while True:
            final_msg = self.check_completed_messages()
            if final_msg is not None:
                return final_msg
            
            # if len(self.possible_messages) < 15:
            #     self.logger.debug(f"Progress {self.progress} @ {self.total_requests}")
                
            rate = self.CHAR_RATE
            xk = self.LAST_ID
            pk = self.pk
            t_prev_update = self.t_prev_update
            snooper = self.snooper

            # compensation for transmission latency
            avg_tx = sum(self.dt_prev_rx) / len(self.dt_prev_rx)
            t0 = default_timer()
            dt_delay_1 = t_prev_update - t0
            T_estim = (avg_tx + dt_delay_1) * rate

            # T_estim = avg_tx * rate
            t0 = default_timer()
            dxk_known, dxk_unknown = self.get_known_total_chars(int(xk), T_estim)
            t1 = default_timer()
            dt_compute = t1-t0

            dxk_uncertain = dxk_unknown + (dt_compute*rate)/12
            dxk = dxk_known + dxk_uncertain 
            # dxk = T_estim / 12

            # Sr = random.randint(8, 12) 
            Sr = self.get_Cr(int(xk + dxk))

            snipe_id = xk + dxk + Sr
            snipe_id = int(snipe_id)

            sniper_sd = 0.41*(dxk_uncertain**0.5)

            try:
                t0 = default_timer()
                msg_id, msg = snooper.get_message(Sr)
                self.total_requests += 1
                t1 = default_timer()
                rtt = t1-t0
            except socket.timeout:
                continue

            snipe_error = msg_id - snipe_id

            t_since_last = t1 - t_prev_update
            self.t_prev_update = t1

            # state propagation
            C1 = rate * t_since_last
            dxk_known, dxk_unknown = self.get_known_total_chars(int(xk), C1)
            N1 = dxk_known + dxk_unknown

            sd1 = 0.41*(dxk_unknown**0.5)
            covar1 = sd1**2

            # our observation error
            dt_Sr = rtt - (Sr*12)/rate
            dt_rx = dt_Sr/2
            self.dt_prev_rx.append(dt_rx)

            C2 = dt_rx * rate
            dxk_known, dxk_unknown = self.get_known_total_chars(msg_id, C2)
            N2 = dxk_known + dxk_unknown

            # standard deviation of observation depends on packet distance
            sd2 = 0.41*(dxk_unknown**0.5)
            covar2 = sd2**2

            zk = msg_id + N2

            xk_pred = xk + N1
            pk_pred = pk + covar1

            ek = zk-xk_pred
            self.logger.debug(f"{self.total_requests}:xk_pred={xk_pred % 1000:.2f} zk={zk % 1000:.2f} kf_error={ek:.2f} snipe_error={snipe_error} | {sniper_sd:.1f}")
            # print(f"\r{self.total_requests}: xk_pred={xk_pred % 1000:.2f} zk={zk % 1000:.2f} kf_error={ek:.2f} snipe_error={snipe_error} | {sniper_sd:.1f}" + " "*10, end="")

            if covar2 != 0 or pk_pred != 0:
                Kk = pk_pred/(pk_pred + covar2)
            else:
                Kk = 1

            xk_next = xk_pred + Kk*(zk - xk_pred)
            pk_next = (1-Kk)*pk_pred

            xk = xk_next
            pk = pk_next

            self.LAST_ID = xk
            self.pk = pk

            self.on_message(msg_id, msg)
            self.sniper.push_error(snipe_error)
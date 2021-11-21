import random
import logging
from timeit import default_timer
from KalmanChannel import KalmanChannel

import threading

# https://stackoverflow.com/questions/6800193/what-is-the-most-efficient-way-of-finding-all-the-factors-of-a-number-in-python
from functools import reduce
def factors(n):    
    return set(reduce(list.__add__, ([i, n//i] for i in range(1, int(n**0.5) + 1) if n % i == 0)))

from PossibleMessage import PossibleMessage, ChunkConflict, EOFMismatch

class OngoingSnipe:
    def __init__(self, target_id, pdf):
        self.target_id = target_id
        self.pdf = pdf

class Solver_V1_MultiKalman:
    def __init__(self, snoopers, snipers, rate, logger=None):
        self.channels = []
        for i, (snooper, sniper) in enumerate(zip(snoopers, snipers)):
            logger = logging.getLogger(f"channel#{i}")
            channel = KalmanChannel(snooper, sniper, logger)
            self.channels.append(channel)

        # Maximum possible number of packets in potential message
        self.MAX_PACKETS = 500 # Based on probability distribution of possible total packets, highly unlikely to be above 500
        # If we are using dense guessing, determine threshold before we start
        # to use greedy sniping
        self.DENSE_GUESS_THRESHOLD = 100

        self.logger = logger or logging.getLogger(__name__)
        
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

        self.snoop_lock = threading.Lock()
        self.snoop_count = threading.Semaphore(0)
        self.IS_THREAD_RUNNING = True
        
        # store all the potential messages
        # key = length of potential message
        # value = PossibleMessage object
        self.possible_messages = set([])

        # store the probability density functions of ongoing requests
        # this way new sniping attempts will avoid overlapping an existing pdf
        self.ongoing_snipes = set([])
    
    # let channel submit a sniping request
    def submit_ongoing_snipe(self, target_id, pdf):
        with self.snoop_lock:
            snipe = OngoingSnipe(target_id, pdf)
            self.ongoing_snipes.add(snipe)
            assert len(self.ongoing_snipes) <= len(self.channels)
            # self.logger.debug(f"Total ongoing snipes={len(self.ongoing_snipes)}")
            return snipe
    
    # removes an ongoing snipe
    def remove_ongoing_snipe(self, snipe):
        with self.snoop_lock:
           self.ongoing_snipes.remove(snipe) 
    
    # get score if we attempt to snipe a particular location
    # we know the probability of an offset occuring
    def get_sniping_score(self, target_id, pdf):
        new_snipe = OngoingSnipe(target_id, pdf)
        combined_snipes = [*list(self.ongoing_snipes), new_snipe]

        score = 0
        for m in self.possible_messages:
            N = len(m)

            combined_pdf = {}
            for snipe in combined_snipes:
                for error, proba in snipe.pdf:
                    i = (snipe.target_id - self.STARTER_ID + error) % N
                    combined_pdf.setdefault(i, 0)
                    combined_pdf[i] += proba

            for i, proba in combined_pdf.items():
                if m[i] is not None:
                    continue

                # if we have a chance of hitting a missing packet
                # add to our sniping score
                # we want to penalise snipes that are strongly overlapping with an existing 
                PROBA_THRESH = 0.7
                PROBA_PENALTY = 0.2
                if proba > PROBA_THRESH:
                    proba = PROBA_THRESH + PROBA_PENALTY*(proba-PROBA_THRESH)
                    proba = min(1, proba)
                score += proba

        return score
    
    # get the actual score
    def get_actual_score(self, target_id):
        with self.snoop_lock:
            score = 0
            for message in self.possible_messages:
                i = target_id-self.STARTER_ID
                if message[i] is None:
                    score += 1
            return score
        
    # greedy search the best Cr to snipe a packet
    def get_Cr(self, id, sniper):
        with self.snoop_lock:
            # random search if cant snipe
            if not self.LAST_ID:
                return random.randint(8,12)

            if self.FOUND_FACTORS or len(self.possible_messages) < self.DENSE_GUESS_THRESHOLD:
                return self.greedy_snipe(id, sniper)
            
            return random.randint(8,12)

    def greedy_snipe(self, id, sniper): 
        hop_scores = []
        pdf = sniper.get_truncated_pdf(N=8)
        for hop in range(7,20):
            score = self.get_sniping_score(id+hop, pdf)
            sort_val = score*1000 - abs(hop-10)
            hop_scores.append((sort_val, score, hop))
        
        _, best_score, best_hop = max(hop_scores, key=lambda h:h[0])
        
        # self.logger.debug(f"Sniping for {(id+best_hop) % 1000} with hop={best_hop} score={best_score:.2f}")
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
                lengths.append(abs(abs(end_id-start_id)))
        
        lengths = set([L for L in lengths if L != 0])
        if len(lengths) == 0:
            self.logger.warning("Ran out of factors, possibly complete")
            return

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
        lengths = factors(abs(end_id-start_id))
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
    # return the number of known packets, and the number of unknown packets
    # default = the mean total characters in a single packet
    # start_id = the packet we are counting from
    # char_count = the desired number of characters we need to reach
    def get_known_total_chars(self, start_id, char_count, default=12):
        with self.snoop_lock:
            i = start_id - self.STARTER_ID

            # we select the longest possible message
            # this is the more conservative since it has more unknown packets
            message = list(self.possible_messages)[-1]
            
            total_unknown = 0
            total_known = 0
            total_char = 0

            # keep going through packets until we reach character count
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
    
    def spawn_channel_thread(self, channel: KalmanChannel):
        msg_id, msg, t_rx = channel.seed(self.CHAR_RATE)

        with self.snoop_lock:
            self.on_message(msg_id, msg)
            self.snoop_count.release()
            if self.LAST_ID is None or self.LAST_ID < msg_id:
                self.LAST_ID = msg_id
                self.t_prev_update = t_rx
        
        # infinite loop while running
        while self.IS_THREAD_RUNNING:
            res = channel.run(self.CHAR_RATE, self.LAST_ID, self.pk, self.t_prev_update, self)
            if res is None:
                continue

            msg_id, msg, t_update, xk_next, pk_next = res

            with self.snoop_lock:
                self.on_message(msg_id, msg)
                self.snoop_count.release()
                if self.LAST_ID < xk_next:
                    self.LAST_ID = xk_next
                    self.pk = pk_next
                    self.t_prev_update = t_update
        
    def run(self):
        self.logger.debug(f"Starting solver run")
        self.logger.info(f"Starting dense guesses from 1 to {self.MAX_PACKETS}")
        self.get_all_guesses()

        threads = [threading.Thread(target=self.spawn_channel_thread, args=[channel]) for channel in self.channels]
        for thread in threads:
            thread.start()

        while True:
            self.snoop_count.acquire()

            with self.snoop_lock:
                final_msg = self.check_completed_messages()

            if final_msg is not None:
                self.IS_THREAD_RUNNING = False
                
                for thread in threads:
                    thread.join()
                
                return final_msg
            
            if len(self.possible_messages) < 15:
                self.logger.debug(f"Progress {self.progress}")
                
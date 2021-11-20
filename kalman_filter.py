# %%
from RealSnooperServer import RealSnooper
from timeit import default_timer
import logging
import socket
from collections import deque

snooper = RealSnooper()
snooper.logger.setLevel(logging.INFO)

# %%
from functools import reduce
def factors(n):    
    return set(reduce(list.__add__, ([i, n//i] for i in range(1, int(n**0.5) + 1) if n % i == 0)))

from PossibleMessage import PossibleMessage, ChunkConflict, EOFMismatch

class KalmanSolver:
    def __init__(self):
        
        self.total_requests = 0
        self.all_packets = []
        self.unique_packets = set([])
        self.EOF_packets = []
        
        # use starter id to get message offset
        self.STARTER_ID = None
        self.MAX_PACKETS = 5000 // 4
        
        # store all the potential messages
        # key = length of potential message
        # value = PossibleMessage object
        self.possible_messages = set([])

        self.get_all_guesses()
    
    # calculate factors and update possible messages 
    def calculate_factors(self):
        if len(self.EOF_packets) < 2:
            return
        
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
            self.possible_messages.remove(m)

    def add_message(self, msg_id, msg):
        packet = (msg_id, msg)
        
        # add packet to relevant queues        
        self.all_packets.append(packet)
        self.unique_packets.add(msg)
        if 0x04 in msg:
            self.EOF_packets.append(packet)
            self.calculate_factors()
        
        # set our first packet
        if self.STARTER_ID is None:
            self.STARTER_ID = msg_id
            return packet
        
    # cull the possible lengths based on 
    # the minimum possible length based on number of non-duplicate packets recieved
    def cull_invalid_lengths(self):  
        nb_unique_packets = len(self.unique_packets)
        for message in list(self.possible_messages):
            N = len(message)
            if N < nb_unique_packets:
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
                    break
                except EOFMismatch:
                    self.possible_messages.remove(message)
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

    # get all possible guesses from 1 to MAX_PACKETS 
    def get_all_guesses(self):
        for n in range(1, self.MAX_PACKETS+1):
            self.possible_messages.add(PossibleMessage(n))

    # return progress of each message as dictionary of
    # {k:v} where k=length, v=#chunks
    @property
    def progress(self):
        return {len(m):m.completed_chunks for m in self.possible_messages}
        
    def on_message(self, msg_id, msg):
        self.add_message(msg_id, msg)
        self.cull_invalid_lengths()
        self.construct_messages()
    
    def get_known_total_chars(self, start_id, T, default=12):
        i = start_id - self.STARTER_ID
        message = list(self.possible_messages)[-1]
        
        total_unknown = 0
        total_known = 0
        total_char = 0

        while total_char < T:
            i += 1
            chunk = message[i]
            if chunk is None:
                total_char += default
                total_unknown += 1
            else:
                total_char += len(chunk)
                total_known += 1

        return (total_known, total_unknown)

# %%
import random 

solver = KalmanSolver()

rate = 1000

Sr = 10
t0 = default_timer()
msg_id, msg = snooper.get_message(Sr)
t1 = default_timer()

rtt = t1-t0
dt_rx = rtt - (Sr*12)/rate
t_prev_update = t1
solver.on_message(msg_id, msg)

dt_prev_rx = deque([dt_rx], maxlen=10)

XK = []
PK = []
EK = []
SNIPE_ERRORS = []

xk = msg_id
pk = 0

for _ in range(1000):
    Sr = random.randint(8, 12) 

    # compensation for transmission latency
    avg_tx = np.array(list(dt_prev_rx)).mean()
    t0 = default_timer()
    dt_delay_1 = t_prev_update - t0
    T_estim = (avg_tx + dt_delay_1) * rate

    # T_estim = avg_tx * rate
    t0 = default_timer()
    dxk_known, dxk_unknown = solver.get_known_total_chars(int(xk), T_estim)
    t1 = default_timer()
    dt_compute = t1-t0

    dxk_uncertain = dxk_unknown + (dt_compute*rate)/12
    dxk = dxk_known + dxk_uncertain 
    # dxk = T_estim / 12

    snipe_id = xk + dxk + Sr
    snipe_id = int(snipe_id)

    sniper_sd = 0.41*(dxk_uncertain**0.5)

    try:
        t0 = default_timer()
        msg_id, msg = snooper.get_message(Sr)
        t1 = default_timer()
        rtt = t1-t0
    except socket.timeout:
        continue

    snipe_error = msg_id - snipe_id

    t_since_last = t1 - t_prev_update
    t_prev_update = t1

    # state propagation
    C1 = rate * t_since_last
    dxk_known, dxk_unknown = solver.get_known_total_chars(int(xk), C1)
    N1 = dxk_known + dxk_unknown

    sd1 = 0.41*(dxk_unknown**0.5)
    covar1 = sd1**2

    # our observation error
    dt_Sr = rtt - (Sr*12)/rate
    dt_rx = dt_Sr/2
    dt_prev_rx.append(dt_rx)

    C2 = dt_rx * rate
    dxk_known, dxk_unknown = solver.get_known_total_chars(msg_id, C2)
    N2 = dxk_known + dxk_unknown

    # standard deviation of observation depends on packet distance
    sd2 = 0.41*(dxk_unknown**0.5)
    covar2 = sd2**2

    zk = msg_id + N2

    xk_pred = xk + N1
    pk_pred = pk + covar1

    ek = zk-xk_pred
    print(f"\rxk_pred={xk_pred:.2f} zk={zk:.2f} kf_error={ek:.2f} snipe_error={snipe_error} | {sniper_sd:.1f}" + " "*10, end="")

    if covar2 != 0 or covar1 != 0:
        Kk = covar1/(covar1 + covar2)
    else:
        Kk = 1

    xk_next = xk_pred + Kk*(zk - xk_pred)
    pk_next = (1-Kk)*pk_pred

    xk = xk_next
    pk = pk_next

    solver.on_message(msg_id, msg)

    XK.append(xk)
    PK.append(pk)
    EK.append(ek)
    SNIPE_ERRORS.append(snipe_error)


# %%
import numpy as np
import matplotlib.pyplot as plt

plt.plot(PK)
plt.show()

plt.plot(EK)
plt.show()

plt.plot(SNIPE_ERRORS)
plt.grid()
plt.show()

# %%
from collections import Counter
# i = -400
# c = Counter(SNIPE_ERRORS[i:min(-1, i+100)])
c = Counter(SNIPE_ERRORS)
plt.bar(list(c.keys()), list(c.values()))
plt.show()

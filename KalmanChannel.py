from collections import deque
from timeit import default_timer
import numpy as np
import socket
import logging

class KalmanChannel:
    def __init__(self, snooper, sniper, logger=None):
        self.snooper = snooper
        self.sniper = sniper
        self.total_requests = 0
        self.dt_prev_rx = deque([], maxlen=10)
        self.logger = logger or logging.getLogger(__name__)
    
    # get first response to seed priors
    def seed(self, rate):
        Sr = 10
        t0 = default_timer()
        msg_id, msg = self.snooper.get_message(Sr)
        self.total_requests += 1
        t1 = default_timer()

        rtt = t1-t0
        dt_rx = rtt - (Sr*12)/rate
        self.dt_prev_rx.append(dt_rx)

        return (msg_id, msg, t1)
    
    def run(self, rate, xk, pk, t_prev_update, solver):
        snooper = self.snooper

        # NOTE: Kalman filter basics
        # https://stackoverflow.com/questions/61486107/how-does-covariance-matrix-p-in-kalman-filter-get-updated-in-relation-to-measu
        # xk = most recent message_id
        # Qk = covariance when propagating using time of most recent message to get xk+1
        # Hk = observation matrix (our observation is of the state directly, so Hk=1)
        # Rk = observation covariance when using network latency of reply and replied message_id
        # zk = observation value (this is our 'observered' value of xk+1)
        # Kk = kalman gain (like the alpha in a discrete low pass filter)

        # STEP 1: Compensate for transmission latency based on last N reading
        # compensation for transmission latency
        avg_tx = np.array(list(self.dt_prev_rx)).mean()
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

        # STEP 2: Compensate as much as possible for transmission latency
        # Sr = random.randint(8, 12) 
        Sr = solver.get_Cr(int(xk + dxk), self.sniper)

        snipe_id = xk + dxk + Sr
        snipe_id = int(snipe_id)

        # NOTE: For a sequence of N packets, this is the uncertainty in the total character length of all packets
        # std = 0.41*sqrt(N)
        sniper_sd = 0.41*(dxk_uncertain**0.5)

        # STEP 3: Perform the snipe and record error and times
        try:
            t0 = default_timer()
            msg_id, msg = snooper.get_message(Sr)
            self.total_requests += 1
            t1 = default_timer()
            rtt = t1-t0
        except socket.timeout:
            return

        snipe_error = msg_id - snipe_id
        t_since_last = t1 - t_prev_update

        # STEP 4: Kalman filter: calculate propagation estimate and covariance
        # Use the time since last reading to propagate state forward
        # Process noise is dictated by uncertainty in number of packets elapsed
        C1 = rate * t_since_last
        dxk_known, dxk_unknown = solver.get_known_total_chars(int(xk), C1)
        N1 = dxk_known + dxk_unknown

        sd1 = 0.41*(dxk_unknown**0.5)
        Qk = sd1**2

        # STEP 5: Kalman filter: calculate observation estimate and covariance
        # Use the replied message_id and the estimated reply latency to get compensated observation with error
        # Calculate our reply latency
        dt_txrx = rtt - (Sr*12)/rate
        dt_rx = dt_txrx/2
        self.dt_prev_rx.append(dt_rx)

        # calculate the number of packets elapsed during that time with errors
        C2 = dt_rx * rate
        dxk_known, dxk_unknown = solver.get_known_total_chars(msg_id, C2)
        N2 = dxk_known + dxk_unknown

        # our compensated observation with errors
        zk = msg_id + N2
        sd2 = 0.41*(dxk_unknown**0.5)
        Rk = sd2**2

        # STEP 6: Kalman filter: perform update step
        # Propagate state and update covariance from Step 4
        xk_pred = xk + N1
        pk_pred = pk + Qk

        ek = zk-xk_pred
        self.logger.debug(f"{self.total_requests}:xk_pred={xk_pred % 1000:.2f} zk={zk % 1000:.2f} kf_error={ek:.2f} msg_id={msg_id % 1000:.0f} snipe_target={snipe_id % 1000:.0f} snipe_error={snipe_error} | {sniper_sd:.1f}")
        # print(f"\rchannel#{self.id}:{self.total_requests}: xk_pred={xk_pred % 1000:.2f} zk={zk % 1000:.2f} kf_error={ek:.2f} snipe_error={snipe_error} | {sniper_sd:.1f}" + " "*10, end="")

        # STEP 7: Kalman filter: Calculate our kalman gain using Rk from Step 5
        if Rk != 0 or pk_pred != 0:
            Kk = pk_pred/(pk_pred + Rk)
        else:
            Kk = 1

        # STEP 8: Kalman filter: update measurement with measurement from Step 5
        xk_next = xk_pred + Kk*(zk - xk_pred)

        # STEP 9: Kalman filter: update the error covariance
        pk_next = (1-Kk)*pk_pred

        xk = xk_next
        pk = pk_next

        self.sniper.push_error(snipe_error)
        return (msg_id, msg, t1, xk, pk)


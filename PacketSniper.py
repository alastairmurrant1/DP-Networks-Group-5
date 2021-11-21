"""
Keeps tracks of recent sniping errors to build a density function
For a given set of masks, it returns the scores based on a heuristic
"""
from collections import deque, Counter
import time

class PacketSniper:
    def __init__(self, maxlen=100):
        self.maxlen = maxlen
        self.errors = deque([])
        self.counts = Counter([])
        self.countsTimes = deque([])
        self.PDF = {}

        self.net_counts = Counter([])
        self.nb_snipes = 0
        

    # update recent error window, counts, and PDF 
    def push_error(self, error):
        self.errors.append(error)
        self.counts[error] += 1
        self.countsTimes.append(time.time())


       # print(f"N before: {len(self.errors)}")
       #gets a time window of 1 sec and observes all errors in last 1 sec
        while (time.time() - self.countsTimes[0] > 1):
            self.countsTimes.popleft()
            del_error = self.errors.popleft()
            self.counts[del_error] -= 1
        
        #print(f"N after: {len(self.errors)}")
        N = len(self.errors)
        self.PDF = {k:v/N for k,v in self.counts.items()}

        self.net_counts[error] += 1
        self.nb_snipes += 1
    
    @property
    def net_PDF(self):
        N = self.nb_snipes
        return {k:v/N for k,v in self.net_counts.items()}

   

    # get the most likely probabilities
    def get_truncated_pdf(self, N=5):
        pdf = list(self.PDF.items())
        pdf = sorted(pdf, key=lambda x:x[1], reverse=True)
        return pdf[:N]

    # index = offset we are sniping at
    # return score = sum of proba[offset] * missing_chunks[offset] for all messages
    def get_score(self, messages, index, threshold=0.01, N=4):
        score = 0
        #for error, proba in self.get_over_range_pdf(N=N):
        for error, proba in self.get_truncated_pdf(N=N):
            # ignore if probability too low
            if proba < threshold:
                continue

            for m in messages:
                N = len(m)
                j = (index + error) % N 
                if m[j] is None:
                    score += proba

        return score
"""
Keeps tracks of recent sniping errors to build a density function
For a given set of masks, it returns the scores based on a heuristic
"""
from collections import deque, Counter

class PacketSniper:
    def __init__(self, maxlen=100):
        self.maxlen = maxlen
        self.errors = deque([], maxlen=maxlen+1)
        self.counts = Counter([])
        self.PDF = {}

        self.net_counts = Counter([])
        self.nb_snipes = 0

    # update recent error window, counts, and PDF 
    def push_error(self, error):
        self.errors.append(error)
        self.counts[error] += 1

        if len(self.errors) > self.maxlen:
            del_error = self.errors.popleft()
            self.counts[del_error] -= 1
        
        N = len(self.errors)
        self.PDF = {k:v/N for k,v in self.counts.items()}
        self.net_counts[error] += 1
        self.nb_snipes += 1
    
    @property
    def net_PDF(self):
        N = self.nb_snipes
        return {k:v/N for k,v in self.net_counts.items()}
    
    # masks = {k:v}
    # k = length of message 
    # v = chunks where None=missing chunk, bytes()=present chunk
    # index = offset we are sniping at
    # return score = sum of proba[offset] * missing_chunks[offset] for all messages
    def get_score(self, messages, index, threshold=0.01):
        score = 0
        for error, proba in self.PDF.items():
            # ignore if probability too low
            if proba < threshold:
                continue
            i=0
            for N, chunks in messages.items():
                i=i+1
                j = (index + error) % N 
                if chunks[j] is None:
                    score += proba
            print(f"i: {i}")

        return score
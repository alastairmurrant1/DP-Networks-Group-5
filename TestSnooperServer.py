import random
import logging

class OffsetGenerator:
    def __init__(self):
        errors = {-1: 558, 0: 282, -2: 163, -3: 16, -4: 1, -6: 1}
        offset_array = []
        for offset, N in errors.items():
            offset_array.extend([-offset]*N)
        self.offset_array = offset_array
    
    def get_value(self):
        return random.choice(self.offset_array)

class TestSnooper:
    def __init__(self, messages, logger=None, offset_generator=None):
        self.inter_response_threshold = 50
        self.inter_response_queue_increment = 1000
        
        self.inter_response_buffer = 0
        self.queue_length = 2
        
        self.MAX_SCORE = 25
        self.Fn = 0
        self.N = 0
        self.total_score = 0
        
        self.messages = messages
        self.current_message = 0

        self.is_closed = False
        
        self.offset_generator = offset_generator
        self.logger = logger or logging.getLogger(__name__)

        self.open_message(self.messages[self.current_message])
        self.reset_score()
    
    def open_message(self, msg):
        self.packets = []
        self.true_msg = msg
        
        msg = bytes(msg + chr(0x04), "utf-8")
        
        i = 0
        N = len(msg)
        
        while i < N:
            msg_len = random.randint(4, 20)
            msg_packet = msg[i:i+msg_len]
            self.packets.append(msg_packet)
            i += msg_len
        
        self.logger.info(f"Serving message #packets={len(self.packets)} #chars={len(msg)}")
    
    def check_inter_response(self, prev_id, next_id):
        inter_response_rate = 0
        for i in range(prev_id, next_id):
            i = i % len(self.packets)
            inter_response_rate += len(self.packets[i])
        
        # Increment snooper queue if enough characters incremented over
        self.inter_response_buffer += inter_response_rate
        if self.inter_response_buffer >= self.inter_response_queue_increment:
            self.queue_length = min(2, self.queue_length+1)
            self.inter_response_buffer = 0
        
        # If inter-response rate too low, reduce snooper queue
        if inter_response_rate < self.inter_response_threshold:
            self.logger.warn("Inter response too low")
            self.queue_length = max(0, self.queue_length-1)
            if self.queue_length == 0:
                self.logger.error("Snooper detected")
    
    @property
    def score(self):
        if self.N == 0:
            return self.MAX_SCORE
        
        return self.MAX_SCORE/self.N * self.total_score
    
    def update_score(self):
        self.N += 1
        self.total_score += 0.9**self.Fn
    
    def reset_score(self):
        self.msg_id = random.randint(0, 1 << 16)
        self.inter_response_buffer = 0
        self.queue_length = 2
        
        self.N = 0
        self.Fn = 0
        self.total_score = 0
    
    def get_message(self, Sr, check=False):
        if self.is_closed:
            raise ValueError("Snooper is closed")
            
        offset = 0 if self.offset_generator is None else self.offset_generator.get_value()
        
        prev_id = self.msg_id
        next_id = (self.msg_id + Sr + offset) % (1 << 63)
        self.msg_id = next_id
        
        self.check_inter_response(prev_id, next_id)
        self.update_score()
        
        msg_packet = self.packets[self.msg_id % len(self.packets)]
        return (self.msg_id, msg_packet)
    
    def post_message(self, msg):
        success = msg == self.true_msg
        if not success:
            self.Fn += 1
        else:
            self.current_message += 1
            
        if self.current_message >= len(self.messages):
            self.is_closed = True
            return 205
        
        if success:
            self.open_message(self.messages[self.current_message])
            return 200
        
        return 406

# Example use
# with open("alice.txt") as fp:
#     data = fp.read()
#     data = data[:1000]
#     snooper = TestSnooper(data)
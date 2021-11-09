import random 

class TestSnooper:
    def __init__(self, msg):
        self.inter_response_threshold = 50
        self.inter_response_buffer = 0
        self.inter_response_queue_increment = 1000
        
        
        self.queue_length = 2
        
        self.open_message(msg)
    
    def open_message(self, msg):
        self.packets = []
        self.msg_id = random.randint(0, 1 << 16)
        
        self.true_msg = msg
        
        msg = bytes(msg + chr(0x04), "utf-8")
        
        i = 0
        N = len(msg)
        
        while i < N:
            # From statistic analysis, we know this is a uniform distribution
            msg_len = random.randint(4, 20)
            msg_packet = msg[i:i+msg_len]
            self.packets.append(msg_packet)
            i += msg_len

    # Perform server actions related to inter-response rate
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
            print("Inter response too low")
            self.queue_length = max(0, self.queue_length-1)
            if self.queue_length == 0:
                print("Snooper detected")
        
    
    def get_message(self, Sr, check=False):
        prev_id = self.msg_id
        next_id = (self.msg_id + Sr) % (1 << 63)
        self.msg_id = next_id
        
        if check:
            self.check_inter_response(prev_id, next_id)
        
        msg_packet = self.packets[self.msg_id % len(self.packets)]
        return (self.msg_id, msg_packet)
    
    def post_message(self, msg):
        return msg == self.true_msg

# Example use
# with open("alice.txt") as fp:
#     data = fp.read()
#     data = data[:1000]
#     snooper = TestSnooper(data)
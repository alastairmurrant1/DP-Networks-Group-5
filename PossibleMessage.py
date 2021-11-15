# In the event a new chunk conflicts with an existing chunk
class ChunkConflict(Exception):
    def __init__(self, message, index, chunk):
        self.message = message
        self.index = index
        self.chunk = chunk

# In the event an EOF chunk occurs twice in two different indices
class EOFMismatch(Exception):
    def __init__(self, message, index, chunk):
        self.message = message
        self.index = index
        self.chunk = chunk

# Handles insertion of chunks into a potential message of fixed length
# Detects chunk conflicts if contents differ, or EOF detected in different index
class PossibleMessage:
    def __init__(self, N):
        self.N = N
        self.chunks = [None]*N
        self.EOF_index = None
        self.completed_chunks = 0
    
    def __hash__(self):
        return self.N
    
    @property
    def is_complete(self):
        rv = self.completed_chunks == self.N
        if rv:
            assert self.EOF_index is not None
        return rv
    
    @property
    def message(self):
        if not self.is_complete:
            return None
        
        i = self.EOF_index+1
        chunks = self.chunks[i:] + self.chunks[:i]
        msg = ''.join((str(chunk, "utf-8") for chunk in chunks))
        msg = msg[:-1]
        return msg
    
    def __len__(self):
        return self.N
        
    def __getitem__(self, index):
        index = index % self.N
        return self.chunks[index]
    
    def __setitem__(self, index, chunk):
        index = index % self.N
        prev_chunk = self.chunks[index]
        
        # chunk already exists
        if prev_chunk == chunk:
            return
        
        # chunk conflict
        if prev_chunk is not None:
            raise ChunkConflict(self, index, chunk)
        
        # EOF conflict
        if 0x04 in chunk:
            if self.EOF_index is not None and self.EOF_index != index:
                raise EOFMismatch(self, index, chunk)
            self.EOF_index = index
        
        self.chunks[index] = chunk
        self.completed_chunks += 1
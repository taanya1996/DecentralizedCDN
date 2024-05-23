from collections import defaultdict, deque

class current_node:
    def __init__(self, IP, node_id, total_nodes, f):
        self.ip = IP
        self.node_id =  node_id  
        self.total_nodes= total_nodes
        self.f = f
        self.received_initial = set()
        self.echo_messages = defaultdict(set)
        self.ready_messages =  defaultdict(set)
        #self.echoed_messages = set()
        self.ready_sent_messages = set()
        self.delivered_messages = set()
        self.buffer = set()
        self.next_message_id = 0
        
class Node:
    def __init__(self, id, IP):
        self.id = id
        self.ip = IP

class Vertex:
    def __init__(self, id=None, round=None, source=None, block=None, strong_edges=None, weak_edges=None):
        self.vertex_id = id #vertex_id is of the form node_id:round_no
        self.round = round
        self.source = source
        self.block = block
        self.strong_edges = strong_edges
        self.weak_edges = weak_edges
    
    def to_dict(self):
        return {
            'vertex_id' : self.vertex_id,
            'round' : self.round,
            'source': self.source,
            'block' : self.block,  
            'strong_edges': [ edge.vertex_id for edge in self.strong_edges] if self.strong_edges else [],
            'weak_edges': [edge.vertex_id for edge in self.weak_edges] if self.weak_edges else []
        }

class Message:
    def  __init__(self, id=None, type=None, message=None, sender=None):
        self.id = id
        self.type = type # INITIAL, ECHO, READY
        self.message = message # message here will be vertex 
        self.sender = sender
    
    def to_dict(self):
        return {
            'id' : self.id,
            'type': self.type,
            'message' : self.message.to_dict() if self.message else None,
            'sender' : self.sender
        }
    

    
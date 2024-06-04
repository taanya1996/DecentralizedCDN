from collections import defaultdict, deque
import hashlib
from ecdsa import SigningKey, SECP256k1
from ecdsa.util import number_to_string, string_to_number
from hashlib import sha256


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
        #for Global Perfect coin
        self.private_key_share = SigningKey.generate(curve=SECP256k1) #each node will get a different private key share
        self.public_key_share = self.private_key_share.get_verifying_key() #TODO should this info be sent to all the nodes?
        self.threshold_signature = ThresholdSignature(total_nodes, f+1)
        self.leaders = {} #leaders for every wave
        self.ips_to_block = []

        
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

class PS_Message:
    def __init__(self, node_id=None, wave=None, signature_share=None):
        self.node_id = node_id # node_id of the Partial Signature
        self.wave = wave #Partial Signature for which wave
        self.signature_share = signature_share.hex()
    
    def to_dict(self):
        return {
            'node_id' : self.node_id,
            'wave': self.wave,
            'signature_share' : self.signature_share
        }

class ThresholdSignature:
    def __init__(self, total_nodes, threshold):
        self.total_nodes = total_nodes
        self.threshold = threshold
        self.signatures = defaultdict(lambda: defaultdict(list)) # stores individual signature by wave and node
        self.threshold_signatures = {} #Combined threshold signatures by wave

    
    
class Message:
    def  __init__(self, id=None, type=None, message_type =None, message=None, sender=None):
        self.id = id
        self.type = type # INITIAL, ECHO, READY
        self.message_type = message_type #vertex or partial_signature
        self.message = message # message here will be vertex/PS_Message. 
        self.sender = sender
    
    def to_dict(self):
        return {
            'id' : self.id,
            'type': self.type,
            'message_type' : self.message_type,
            'message' : self.message.to_dict() if self.message else None,
            'sender' : self.sender
        }
    

    
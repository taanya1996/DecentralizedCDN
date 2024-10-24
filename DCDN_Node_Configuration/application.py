import sys
sys.path.append('/home/ec2-user/.local/lib/python3.9/site-packages')
from flask import Flask, request, jsonify, Response
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
import subprocess
import requests
import json
import threading
import request_rate_track
import definitions
from ecdsa import SigningKey, SECP256k1
from ecdsa.util import number_to_string, string_to_number
from hashlib import sha256
import socket
import logging
import os
import csv
import random
from secretshare import Secret, SecretShare, Share
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.lines as mlines

app = Flask(__name__)
logging.basicConfig(level = logging.INFO) 
werkzeug_log = logging.getLogger('werkzeug')
werkzeug_log.setLevel(logging.ERROR)

nodes = {} # {id: CDN_Node}
CDN_IPs = ['54.215.43.60', '34.201.142.18', '52.74.244.78', '18.132.44.229']
pbft_port = 8080
my_node = definitions.current_node(IP='54.215.43.60',node_id=1, total_nodes= 4, f=1) #TOBE set separately for each node.
pbft_control_messages = deque() #these are the reliable broadcast messages. 
pbft_control_messages_lock = threading.Lock()
to_block_ips = defaultdict() #{vertex_id: Identified_time}
to_block_ips_lock = threading.Lock()
to_unblock_ips = defaultdict() #{vertex_id: Identified_time}
to_unblock_ips_lock = threading.Lock()
rbcast_ips = defaultdict() #{vertex_id: time}
vertex_time_delta =  defaultdict(list) #{vertex_id: [vertex_creation_time, time_for_rbcast, time_to_commit, time_for_consensus]}
visualize_counter = 1
dag_round_rate = 0
dag_rate_arr = []

# Vertices for the DAGRider is above the reliable Broadcast layer.
DAG = defaultdict(set)

def get_server_ip():
    try:
        hostname = socket.gethostname()
        server_ip = socket.gethostbyname(hostname)
        return server_ip
    except Exception as e:
        logging.error('Error obtaining private IP address.')

def set_my_node():
    global my_node
    server_ip = get_server_ip()
    if server_ip == '172.30.1.57':
        #node1
        my_node = definitions.current_node(IP='54.215.43.60',node_id=1, total_nodes= 4, f=1) 

    elif server_ip == '172.30.0.49':
        #node2
        my_node = definitions.current_node(IP='34.201.142.18',node_id=2, total_nodes= 4, f=1) 
    elif server_ip == '172.30.0.168':
        #node3
        my_node = definitions.current_node(IP='52.74.244.78',node_id=3, total_nodes= 4, f=1) 
    elif server_ip == '172.31.45.119':
        #node4
        my_node = definitions.current_node(IP='18.132.44.229',node_id=4, total_nodes= 4, f=1) 
    else:
        logging.error('Error setting up nodes')
        exit(1)

def initialize_nodes():
    for i in range(1, my_node.total_nodes+1):
        nodes[i] =  definitions.Node(i, CDN_IPs[i-1])
            
#--------------RELIABLE BROADCAST SECTION------------------

def reliable_bcast(message, message_type):
    '''
    param: message - Object of Vertex class/ Threshold Signature.
    '''
    
    new_message = definitions.Message()
    with my_node.next_message_id_lock:
        my_node.next_message_id +=1
        message_id = str(my_node.node_id)+':'+str(my_node.next_message_id)
    new_message.id = message_id
    new_message.message_type = message_type
    new_message.message = message
    new_message.type = 'INITIAL'
    new_message.sender = my_node.node_id
    
    message_dict = new_message.to_dict()
    message_json = json.dumps(message_dict)
    
    send_initial(message_json)

def send_initial(message):
    #send messages
    for node in nodes:
        if nodes[node].id != my_node.node_id:
            #send INITIAL Messages to all
            http_send_POST(message, nodes[node].ip)
            
        else:
            #how to send a message to self?
            with pbft_control_messages_lock:
                pbft_control_messages.append(message)
    

def handle_initial(message):
    message_id = message['id']
    if message_id not in my_node.received_initial:
        my_node.received_initial.add(message_id)
        broadcast_echo(message)
    

def broadcast_echo(message):
    # Serialize the original object to a JSON string
    json_string = json.dumps(message)

    # Deserialize the JSON string back to a new Python dictionary (deep copy)
    new_message = json.loads(json_string)
    new_message['type'] = 'ECHO'
    new_message['sender'] = my_node.node_id
    
    for node in nodes:
        #new_message has to be serialized
        new_message = json.dumps(new_message)
        if nodes[node].id != my_node.node_id:
            http_send_POST(new_message, nodes[node].ip)
        else:
            #send to self node
            with pbft_control_messages_lock:
                pbft_control_messages.append(new_message)
            

def handle_echo(message):
    message_id = message['id']
    my_node.echo_messages[message_id].add(message['sender'])
    
    if len(my_node.echo_messages[message_id]) >= 2 * my_node.f + 1:
        #Am I handling duplicate echoes?
        if message_id not in my_node.ready_sent_messages:
            broadcast_ready(message)
        
    
def broadcast_ready(message):
    message_id = message['id']
    # Serialize the original object to a JSON string
    json_string = json.dumps(message)

    # Deserialize the JSON string back to a new Python dictionary (deep copy)
    new_message = json.loads(json_string)
    new_message['type'] = 'READY'
    new_message['sender'] = my_node.node_id
    
    for node in nodes:
        #new_message has to be serialized
        new_message = json.dumps(new_message)
        if nodes[node].id != my_node.node_id:
            http_send_POST(new_message, nodes[node].ip)
        else:
            #send to self
            with pbft_control_messages_lock:
                pbft_control_messages.append(new_message)
    my_node.ready_sent_messages.add(message_id)     

def handle_ready(message):
    message_id = message['id']
    my_node.ready_messages[message_id].add(message['sender'])
    if len(my_node.ready_messages[message_id]) >= my_node.f +1 :
        #send ready if not already sent ; Ready to Ready Transition:
        if message_id not in my_node.ready_sent_messages:
            broadcast_ready(message)
    
    if len(my_node.ready_messages[message_id]) >= 2 * my_node.f + 1 and message_id not in my_node.delivered_messages: #deliver the message only once.
        deliver_message(message)
     
     
def deliver_message(message):
    
    logging.info(f"ReliableBcast Delivery - message_type: {message['message_type']} message ID: {message['id']}")
    if message['message_type'] == 'V':
        #deliver the vertex
        deliver_vertex(message)
        return
    elif message['message_type'] == 'TS':
        #deliver the threshold signature.
        deliver_partial_signature(message)
        return 
    elif message['message_type'] == 'SS':
        #deliver secret share
        deliver_secret_share(message)
        return
    logging.error('Something is wrong delivering the message')

def deliver_secret_share(message):
    '''
    The secret share is accepted through reliable bcast.
    '''
    ss_message = message['message']
    node_id = ss_message['node_id']
    wave = ss_message['wave']
    secret_share = Share()
    secret_share.from_hex(ss_message['secret_share'])
    
    my_node.delivered_messages.add(message['id'])
    receive_secret_share(node_id, wave, secret_share)

def deliver_partial_signature(message):
    '''
    The partial signature is accepted through reliable bcast.
    '''
    ps_message = message['message']
    node_id = ps_message['node_id']
    wave = ps_message['wave']
    signature_share = bytes.fromhex(ps_message['signature_share'])
    
    my_node.delivered_messages.add(message['id'])
    receive_signature(node_id, wave, signature_share)    
    

def deliver_vertex(message):
    #deliver to the DAG Layer
    #create a vertex out of message
    new_vertex = definitions.Vertex()
    new_vertex.vertex_id = message['message']['vertex_id']
    new_vertex.round = message['message']['round']
    new_vertex.source = message['message']['source']
    new_vertex.block = message['message']['block']
    strong_edges = []
    for edge_id in message['message']['strong_edges']:
        id_list = edge_id.split(":") #node_id:round_no
        edge_round =  id_list[1]
        for vertex in DAG[int(edge_round)]:
            if edge_id == vertex.vertex_id:
                strong_edges.append(vertex)
    
    weak_edges =[]
    for edge_id in message['message']['weak_edges']:
        id_list = edge_id.split(":") #node_id:round_no
        edge_round =  id_list[1]
        for vertex in DAG[int(edge_round)]:
            if edge_id == vertex.vertex_id:
                weak_edges.append(vertex)
    
    new_vertex.strong_edges = strong_edges
    new_vertex.weak_edges = weak_edges
    logging.info(f"VertexDelivery - MessageId: {message['id']} VertexID: {new_vertex.vertex_id}")
    my_node.delivered_messages.add(message['id'])
    
    #Identify the time_delta for reliable_bcast
    if new_vertex.source == my_node.node_id:
        time_delta = time.time() - vertex_time_delta[new_vertex.vertex_id][0]
        vertex_time_delta[new_vertex.vertex_id].append(time_delta)
       
    #vertex is constructed. Deliver it to the DAG Layer
    r_delivery_to_DAG(new_vertex)
    
#--------------/RELIABLE BROADCAST SECTION------------------

#--------------DAG Layer------------------
def path(v,u):
    '''
    param: v,u : objects of Vertex class
    '''
    
    visited = set()
    
    def dfs(current_vertex):
        if current_vertex == u:
            return True
        
        visited.add(current_vertex)
        
        for vertex in current_vertex.strong_edges + current_vertex.weak_edges:
            if vertex not in visited:
                if dfs(vertex):
                    return True
        return False
    
    return dfs(v)

def strong_path(v,u):
    '''
    Strong Path from v to u
    param: v,u : objects of Vertex class
    '''
    
    visited = set()
    
    def dfs(current_vertex):
        if current_vertex == u:
            return True
        
        visited.add(current_vertex)
        
        for vertex in current_vertex.strong_edges:
            if vertex not in visited:
                if dfs(vertex):
                    return True

        return False
    
    return dfs(v)


dag_round = 1 # TODO check the initial value. Also DAG 1 round values are hardcoded. TODO
dag_round_lock = threading.Lock()
dag_buffer = [] 
dag_buffer_lock = threading.Lock()
create_vertex = False
block_to_propose = []
block_to_propose_lock = threading.Lock()


def VertexInDAG(vertex):
    '''
    param vertex: Object of Vertex class
    '''
    v_round = vertex.round
    if vertex in DAG[v_round]:
        return True
    
    return False

def add_vertex_to_DAG(vertex):
    '''
    param vertex: Object of Vertex class
    '''
    v_round = vertex.round
    DAG[v_round].add(vertex) 
 
def set_weak_edges(vertex):
    '''
    param vertex: Object of Vertex class
    ''' 
    vertex.weak_edges = []
    for round in range(vertex.round-2, 0, -1):
        for u_vertex in DAG[round]:
            if path(vertex, u_vertex)==False:
                #this is the weak edge
                vertex.weak_edges.append(u_vertex)
    
    logging.info(f'No of weak edges for the vertex {vertex.vertex_id}: {len(vertex.weak_edges)}')
    
    
def remove_vertex_from_DAG_Buffer(vertices_to_remove_from_dag_buffer):
    '''
    Removes the processed vertex from DAG buffer.
    '''
    
    for vertex in vertices_to_remove_from_dag_buffer:
        with dag_buffer_lock:
            dag_buffer.remove(vertex)
    
    
def DAG_construction_procedure():
    '''
    This will be a thread continuously running to build the DAG
    '''
    global dag_round
    global dag_round_rate
    global dag_rate_arr
    while (True):
        
        with dag_buffer_lock:
            init_buf_len =  len(dag_buffer)
        
        to_remove_from_buffer = []
       
        for buf_ind in range(0, init_buf_len):
            with dag_buffer_lock:
                buffer_vertex = dag_buffer[buf_ind]
            flag = True
            with dag_round_lock:
                if(buffer_vertex.round <= dag_round):
                    for vertex in buffer_vertex.strong_edges + buffer_vertex.weak_edges:
                        if not VertexInDAG(vertex):
                            #this buffer vertex cannot be added to dag
                            flag = False
                            break
                    if flag:
                        #then add the buffer_vertex to dag and remove the buffer_vertex from dag_buffer.
                        add_vertex_to_DAG(buffer_vertex)
                        to_remove_from_buffer.append(buffer_vertex)
    
        #Remove the processed vertex from dag_buffer
        remove_vertex_from_DAG_Buffer(to_remove_from_buffer)
        
        with dag_round_lock:
            if len(DAG[dag_round]) >= 2*my_node.f +1:
                if dag_round%4==0:
                    # handle wave_ready
                    wave_ready(dag_round//4)
                    
                dag_round = dag_round +1
                time_delta = time.time() - dag_round_rate
                dag_round_rate = time.time() 
                dag_rate_arr.append(time_delta)
                
                if dag_round%20 ==0:
                    with open(f"metrics/dag_round_rate_{my_node.node_id}.csv", mode="a") as file:
                        writer = csv.writer(file)
                        writer.writerows([[item] for item in dag_rate_arr])
                        dag_rate_arr = []
                        
                new_vertex = create_new_vertex(dag_round)
                reliable_bcast(new_vertex, 'V')
            
def create_new_vertex(round):
    '''
    Procedure for creating new vertex.
    '''
    logging.info(f'Creating vertex for round {round}. Block To propose: {block_to_propose}')
    #create vertex for new round here. 
    #If no block to propose. Then empty block is proposed.
    with block_to_propose_lock:
        if(len(block_to_propose)==0):
            block = []
        else:
            logging.info('There are some IPs to Block')
            block = block_to_propose
    
    vertex_id = str(my_node.node_id) + ':' + str(round) 
    source = my_node.node_id
    if(round == 1):
        #round1 will not reference anything.
        new_vertex =  definitions.Vertex(vertex_id, round, source, block, [], [])
        # rbcast_ips[vertex_id] = time.time()
        vertex_time_delta[vertex_id].append(time.time())
        return new_vertex
    strong_edges = list(DAG[round-1])
    logging.info(f'No of strong edges for the vertex {vertex_id}: {len(strong_edges)}')
    new_vertex = definitions.Vertex(vertex_id,round, source, block, strong_edges)
    #set weak edges
    set_weak_edges(new_vertex)
    # rbcast_ips[vertex_id] = time.time()
    vertex_time_delta[vertex_id].append(time.time())
    return new_vertex
    

def r_delivery_to_DAG(vertex):
    # Handle 1st round nodes. They will not have any previous references.
    if vertex.round == 1:
        with dag_buffer_lock:
            dag_buffer.append(vertex)
        return 
     
    if len(vertex.strong_edges) >= 2 * my_node.f + 1:
        with dag_buffer_lock:
            dag_buffer.append(vertex) 
    
#--------------/DAG Layer-----------------------

#--------------Global Perfect Coin-----------------------
def generate_secret_share(node_id, wave):
    share = Share(node_id, wave)
    ss_message = definitions.SS_Message(node_id, wave, share)
    reliable_bcast(ss_message, 'SS')
    
def receive_secret_share(node_id, wave, secret_share):
    my_node.secret_share.secret_shares[wave][node_id] = secret_share
    
    if len(my_node.secret_share.secret_shares[wave]) >= my_node.secret_share.threshold:
        combine_secret_shares(wave)
        #If combined secret is computed then compute global perfect coin
        if get_secret(wave):
            compute_global_coin(wave)

def combine_secret_shares(wave):
    if wave not in my_node.secret_share.secrets:
        node_ids = my_node.secret_share.secret_shares[wave].keys()
        shares = [] 
        for node_id in node_ids:
            shares.append(my_node.secret_share.secret_shares[wave][node_id]) 
        shamir_secret_share = SecretShare(my_node.secret_share.threshold, my_node.secret_share.total_nodes, shares=shares)
        secret = shamir_secret_share.combine()
        my_node.secret_share.secrets[wave] = secret

def get_secret(wave):
    return my_node.secret_share.secrets.get(wave, None)


def compute_global_coin(wave):
    if wave in my_node.leaders:
        return #Global perfect coin is already computed and leader is chosen for the wave.
    
    combined_secret = get_secret(wave)
    
    if combined_secret:
        combined_secret = sum([ord(char) for char in str(combined_secret)])
        leader = (combined_secret % my_node.total_nodes) + 1
        # if leader == 3:
        #     leader = random.choice([1,2,4])
        my_node.leaders[wave] = leader
        


def choose_leader(w):
    '''
    selects leader node for the wave w. 
    Need to implement global perfect coin here. 
    '''
    #TODO check logic
    if my_node.leaders.get(w, None):
        return my_node.leaders[w]

    if not my_node.secret_share.secret_shares.get(w, None) or not my_node.secret_share.secret_shares[w].get(my_node.node_id, None):
        generate_secret_share(my_node.node_id, w)
    
    while not my_node.leaders.get(w,None):
        #time.sleep(1)
        pass
    
    logging.info(f'Leader for the wave {w} is {my_node.leaders.get(w,None)}')
    return my_node.leaders.get(w, None) 

#--------------/Global Perfect Coin-----------------------


#--------------DAGRider-----------------------
decided_wave = 0
delivered_dag_vertices = []
leader_stack = [] # this is a stack with push, pop functionalities.


    
def get_wave_vertex_leader(w):
    '''
    Return the leader vertex for wave w.
    param (w) : wave number.
    '''
    leader_node = choose_leader(w) #TODO check logic here
    round_one_wave = (w-1)*4 + 1
    for vertex in DAG[round_one_wave]:
        if(vertex.source) == leader_node:
            return vertex
    
    return None

def strong_path_from_round4(w, v_leader):
    '''
    param: w - wave
    v_leader = leader_vertex
    '''
    round =  4*w
    
    count = 0
    for vertex in DAG[round]:
        if strong_path(vertex, v_leader):
            count +=1
    
    if count >= 2* my_node.f + 1:
        return True
    return False

def wave_ready(w):
    '''
    The function gets signal from DAG construction layer
    '''
    global decided_wave
    leader_vertex = get_wave_vertex_leader(w)
        
    if leader_vertex==None:
        logging.info('Leader vertex is None. Hence, returning from wave_ready.')
        visualize_dag()
        return 
    if not strong_path_from_round4(w, leader_vertex):
        logging.info('No 2f+1 strong paths for leader from round 4.')
        visualize_dag()
        return 
    
    leader_stack.append(leader_vertex)
    for wave_prime in range(w-1,decided_wave, -1):
        leader_vertex_prime = get_wave_vertex_leader(wave_prime)
        if leader_vertex_prime!=None and strong_path(leader_vertex,leader_vertex_prime):
            leader_stack.push(leader_vertex_prime)
            leader_vertex = leader_vertex_prime
    decided_wave = w
    if len(leader_stack)>1:
        visualize_dag()
    order_vertices(leader_stack)
    
def order_vertices(leader_stack):
    my_node.ips_to_block = []
    dag_vertices_ids_delivered = set()
    while(len(leader_stack)>0):
        leader_vertex = leader_stack.pop()
        vertices_to_deliver = defaultdict(set)
        for round in range(1, leader_vertex.round):
            for vertex in DAG[round]:
                if(path(leader_vertex, vertex) and vertex not in delivered_dag_vertices):
                    vertices_to_deliver[vertex.round].add(vertex)
        
        print(f'Vertices delivered are: ', end=" ")
        for round in vertices_to_deliver:
            for vertex in sorted(vertices_to_deliver[round], key=lambda x: x.vertex_id):
                print(vertex.vertex_id, end=" ")
                a_deliver(vertex)
                dag_vertices_ids_delivered.add(vertex.vertex_id)
                delivered_dag_vertices.append(vertex)
        print()
          
    os.makedirs("metrics", exist_ok=True)
    
    vertex_time_delta_file_name = f"metrics/vertex_time_delta_node_{my_node.node_id}.csv"
    file_exists = os.path.exists(vertex_time_delta_file_name)
    
    with open(vertex_time_delta_file_name, mode="a", newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['StartTime', 'TimeDeltaRbcast', 'TotalTimeDeltaCommit', 'TimeDeltaConsensus'])
        
        # print(f"Vertex_time_delta during ordering: {vertex_time_delta}" )
        for vertex_id in dag_vertices_ids_delivered:
            if vertex_id in vertex_time_delta:
                current_time = time.time()
                total_time_delta = current_time - vertex_time_delta[vertex_id][0]
                vertex_time_delta[vertex_id].append(total_time_delta)

                consensus_time_delta = total_time_delta- vertex_time_delta[vertex_id][1]
                vertex_time_delta[vertex_id].append(consensus_time_delta)
                writer.writerow(vertex_time_delta[vertex_id])
                vertex_time_delta.pop(vertex_id)
            
    block_file_name = f"metrics/block_time_delta_node_{my_node.node_id}.csv"
    file_exists = os.path.exists(block_file_name)
    
    with to_block_ips_lock:
        for vertex_id in list(to_block_ips.keys()):
            if vertex_id in dag_vertices_ids_delivered:
                identified_time = to_block_ips.pop(vertex_id)
                block_time = time.time()
                with open(block_file_name, mode='a', newline='') as file:
                    writer = csv.writer(file)
                    if not file_exists:
                        writer.writerow(['Nnodes', 'TimeIdentified', 'TimeBlocked', 'TimeDelta'])                    
                    writer.writerow([my_node.total_nodes, identified_time, block_time, block_time-identified_time])
                visualize_dag()
                
    unblock_file_name = f"metrics/unblock_time_delta_node_{my_node.node_id}.csv"
    file_exists = os.path.exists(unblock_file_name)
    
    with to_unblock_ips_lock:
        for vertex_id in list(to_unblock_ips.keys()):
            if vertex_id in dag_vertices_ids_delivered:
                identified_time = to_unblock_ips.pop(vertex_id)
                unblock_time = time.time()
                with open(unblock_file_name, mode='a', newline='') as file:
                    writer = csv.writer(file)
                    if not file_exists:
                        writer.writerow(['Nnodes', 'TimeIdentified', 'TimeUnblocked', 'TimeDelta'])                    
                    writer.writerow([my_node.total_nodes, identified_time, unblock_time, unblock_time-identified_time])
                visualize_dag()
                
    request_rate_track.update_blocklist(my_node.ips_to_block)
    
def a_deliver(vertex):
    '''
    call application logic to block.
    '''
    block = vertex.block
    for ip in block:
        if ip not in my_node.ips_to_block:
            my_node.ips_to_block.append(ip)
    
            
#--------------/DAGRider-----------------------

#--------------Application Logic---------------
windows = defaultdict(deque) 
windows_lock = threading.Lock()
request_threshold = 50
window_duration = timedelta(minutes=1)
blocked_ips = set()
blocked_ips_lock = threading.Lock()

def review_ips_in_window():
    global windows
    global window_duration 
    global request_threshold
    global blocked_ips
    global block_to_propose
    
    while(True):
        for ip in windows:
            with windows_lock:
                while(windows[ip] and (datetime.now() - windows[ip][0] > window_duration) ): #TODO check condition logic
                    windows[ip].popleft()
            
            with windows_lock:
                if len(windows[ip])< request_threshold:
                    if ip in blocked_ips:
                        with dag_round_lock:
                            with blocked_ips_lock:
                                blocked_ips.remove(ip)
                                with block_to_propose_lock:
                                    block_to_propose=list(blocked_ips)
                            with to_unblock_ips_lock:
                                vertex_id = f"{my_node.node_id}:{dag_round+1}"
                                to_unblock_ips[vertex_id] = time.time()
                                logging.info(f"Alert: IP {ip} has been identified to be removed from blocked list. ")
        time.sleep(1)
    

def traffic_rate_tracking():
    '''
    The function continously parses the new log entry in the nginx log to track the rate of request from each IP.
    '''
    global block_to_propose
    global windows
    global blocked_ips
    
    request_rate_track.clear_blocklist()
    
    log_file = '/var/log/nginx/access.log'
    request_threshold = 50
    window_duration = timedelta(minutes=1)
    
    #windows = defaultdict(deque) #Dictionary with IP as key and deque as values holding the timestamp
    
    
    with open(log_file, 'r') as file:
        file.seek(0,2)
        
        while(True):
            log_line = file.readline()
            if not log_line:
                #time.sleep(1)
                continue
            
            ip, timestamp =request_rate_track.parse_line(log_line)
            
            with windows_lock:
                while windows[ip] and windows[ip][0] < timestamp - window_duration:
                    windows[ip].popleft() #remove entries that are older than 5 min window period.
            
            with windows_lock:   
                windows[ip].append(timestamp)
            
            #check whether the corresponding IP has exceeded the threshold
            if len(windows[ip]) >= request_threshold:
                if ip not in blocked_ips:
                    with dag_round_lock:            
                        with blocked_ips_lock:
                            blocked_ips.add(ip)
                            with block_to_propose_lock:
                                block_to_propose=list(blocked_ips)
                        with to_block_ips_lock:
                            vertex_id = f"{my_node.node_id}:{dag_round+1}"
                            to_block_ips[vertex_id] = time.time()
                          
                       
            else:
                if ip in blocked_ips:
                    with dag_round_lock:
                        with blocked_ips_lock:
                            blocked_ips.remove(ip)
                            with block_to_propose_lock:
                                block_to_propose=list(blocked_ips)
                        with to_unblock_ips_lock:
                            vertex_id = f"{my_node.node_id}:{dag_round+1}"
                            to_unblock_ips[vertex_id] = time.time()
                        logging.info(f"Alert: IP {ip} has been identified to be removed from blocked list. ")
                            

#--------------/Application Logic---------------

#--------------FLASK ENDPOINT-------------------
@app.route('/pbft', methods=['POST'])
def pbft_endpoint():
    '''
    Receives all the PBFT control messages over POST method and 
    append the messages to the pbft_control_messages queue.
    '''
    try:
        data = request.get_json()
        with pbft_control_messages_lock:
            pbft_control_messages.append(data)

        # Return a success response
        return Response(status=200)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


def http_send_POST(message, IP):
    url = 'http://' + IP + ':' + str(pbft_port) +'/pbft'
    #message_dict = message.to_dict()
    #message_json = json.dumps(message_dict)
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(url, data=message, headers=headers)
    except requests.exceptions.RequestException as e:
        logging.error(f"Request Failed with error {e}")
    

def process_messages():
    '''
    Pops the messages from the pbft_control_messages one by one and process it.
    All the messages here are Reliable Broadcast messages. 
    '''
    
    while(True):
        if pbft_control_messages:
            with pbft_control_messages_lock:
                message = pbft_control_messages.popleft()
            while(type(message)==str):
                message = json.loads(message) # for deserialization TODO Fix multiple levels of serialization
            if message['type']== 'INITIAL':
                handle_initial(message)
            elif message['type'] == 'ECHO':
                handle_echo(message)
            elif message['type'] == 'READY':
                handle_ready(message)
            
        else:
            #no messages yet in the queue. So sleep welll!!!!!
            #time.sleep(1)
            pass
    
    
def start_flask():
    app.run(host='0.0.0.0', port=pbft_port)

#------------------/FLASK ENDPOINT----------------------
    
#------------------DAG Visualization--------------------

def visualize_dag():
    global visualize_counter
    logging.info("Visualizing DAG")
    G = nx.DiGraph()
    
    latest_round = dag_round
    
    latest_wave = latest_round//4
    if latest_round%4>0:
        latest_wave +=1
    
    start_wave = max(1, latest_wave-2)
    start_round = (start_wave-1)*4 + 1
    pos = {}  
    labels = {}
    colors = []
    for round in range(start_round, latest_round+1):
        for j,vertex in enumerate(sorted(DAG[round], key=lambda vertex: vertex.vertex_id)):
            G.add_node(vertex)
            if round%4 ==1:
                if (round//4 +1) in my_node.leaders and vertex.source == my_node.leaders[(round//4+1)]:
                    colors.append('red')
                else:
                    colors.append('lightblue')
            else:
                colors.append('lightblue')
            if round!=start_round:
                for edge in vertex.strong_edges:
                    if edge.round >=start_round:
                        G.add_edge(vertex, edge, edge_type='strong')
                
                for edge in vertex.weak_edges:
                    if edge.round >=start_round:
                        G.add_edge(vertex, edge, edge_type='weak')
            
            pos[vertex] = (round-start_round+1, -vertex.source+1)
            labels[vertex] = vertex.vertex_id        
    plt.figure(figsize=(20, 8))
    
    #Drawing nodes
    nx.draw(G, pos, with_labels=False, node_color=colors)
    
    nx.draw_networkx_labels(G, pos, labels, font_color='black')
    
    strong_edges = [(u, v) for u, v, d in G.edges(data=True) if d['edge_type'] == 'strong']
    nx.draw_networkx_edges(G, pos, edgelist=strong_edges, edge_color='blue')
    
    weak_edges = [(u, v) for u, v, d in G.edges(data=True) if d['edge_type'] == 'weak']
    nx.draw_networkx_edges(G, pos, edgelist=weak_edges, edge_color='lightgrey', style='dashed')
            
    plt.title('DAG of vertices')
    
    # Create custom lines for the legend to represent what each line style means
    strong_edge_legend = mlines.Line2D([], [], color='blue', linestyle='solid', label='Strong Edge')
    weak_edge_legend = mlines.Line2D([], [], color='lightgrey', linestyle='dashed',  label='Weak Edge')

    # Add the legend to the plot
    plt.legend(handles=[strong_edge_legend, weak_edge_legend], loc='upper left')
    
    # plt.tight_layout()
    plt.savefig(f"plot_node{my_node.node_id}_{visualize_counter}.png")
    visualize_counter +=1
    logging.info("DAG visualization completed")

#------------------/DAG Visualization-------------------    
        
def initiate_DAG_system():
    '''
    Create a new vertex for round 1 with empty block and start the DAG cycle
    '''
    global dag_round_rate
    with dag_round_lock:
        first_vertex = create_new_vertex(dag_round)
        dag_round_rate = time.time()
        
    reliable_bcast(first_vertex, 'V')
    
if __name__ == '__main__':
    set_my_node()
    logging.info(f'node IP: {my_node.ip}')
    initialize_nodes()
    
    #create a thread for flask application.
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    
    # Create a thread for the traffic monitoring
    traffic_thread = threading.Thread(target=traffic_rate_tracking)
    traffic_thread.daemon = True
    
    # Create a thread for reviewing the ips in window
    window_ips_review_thread = threading.Thread(target=review_ips_in_window)
    window_ips_review_thread.daemon = True
    
    # Create a thread for message processing
    message_processing_thread = threading.Thread(target=process_messages)
    message_processing_thread.daemon = True
    
    # Create a thread for DAG Construction.
    dag_construction_thread = threading.Thread(target=DAG_construction_procedure)
    dag_construction_thread.daemon = True

    # Start all threads
    flask_thread.start()
    traffic_thread.start()
    window_ips_review_thread.start()
    message_processing_thread.start()
    dag_construction_thread.start()
    
    #Initiate the system here.
    option = 'N'
    
    while option == 'N':
        time.sleep(2)
        option = input("Are we good to initiate the DAG system? Y/N")
    
    initiate_DAG_system()
        
    # Keep the main thread alive
    flask_thread.join()
    traffic_thread.join()
    window_ips_review_thread.join()
    message_processing_thread.join()
    dag_construction_thread.join()
    
    
    
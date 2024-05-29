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


app = Flask(__name__)
nodes = {} # {id: CDN_Node}
CDN_IPs = ['54.215.43.60', '34.201.142.18', '52.74.244.78', '18.132.44.229']
pbft_port = 8080
my_node = definitions.current_node(IP='54.215.43.60',node_id=1, total_nodes= 4, f=1)
pbft_control_messages = deque() #these are the reliable broadcast messages. 
# Vertices for the DAGRider is above the reliable Broadcast layer.
DAG = defaultdict(set)

def initialize_nodes():
    for i in range(1, my_node.total_nodes+1):
        nodes[i] =  definitions.Node(i, CDN_IPs[i-1])
            
#--------------RELIABLE BROADCAST SECTION------------------

def reliable_bcast(vertex):
    '''
    param: vertex - Object of Vertex class
    '''
    my_node.next_message_id +=1
    new_message = definitions.Message()
    message_id = str(my_node.node_id)+':'+str(my_node.next_message_id)
    new_message.id = message_id
    new_message.message = vertex
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
            pbft_control_messages.append(new_message)
    my_node.ready_sent_messages.add(message_id)     

def handle_ready(message):
    message_id = message['id']
    my_node.ready_messages[message_id].add(message['sender'])
    if len(my_node.ready_messages[message_id]) >= my_node.f +1 :
        #send ready if not already sent ; Ready to Ready Transition:
        if message_id not in my_node.ready_sent_messages:
            broadcast_ready(message)
    
    if len(my_node.ready_messages[message_id]) >= 2 * my_node.f + 1 and message_id not in my_node.delivered_messages:
        deliver_message(message)
        

def deliver_message(message):
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
            if edge_id == vertex.edge_id:
                strong_edges.append(vertex)
    
    weak_edges =[]
    for edge_id in message['message']['weak_edges']:
        id_list = edge_id.split(":") #node_id:round_no
        edge_round =  id_list[1]
        for vertex in DAG[int(edge_round)]:
            if edge_id == vertex.edge_id:
                weak_edges.append(vertex)
    
    new_vertex.strong_edges = strong_edges
    new_vertex.weak_edges = weak_edges
    print('Accepted message: ', message['id'], 'delivered the vertex with id: ', new_vertex.vertex_id)
    my_node.delivered_messages.add(message['id'])
    #vertex is constructed. Deliver it to the DAG Layer
    #TODO
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


dag_round = 1 # TODO check the initial value
dag_buffer = [] # or SET? TODO
create_vertex = False
block_to_propose = []

def VertexInDAG(vertex):
    '''
    param vertex: Object of Vertex class
    '''
    v_round = vertex.round()
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
                vertex.weak_edge.append(u_vertex)
    

def DAG_construction_procedure():
    '''
    This will be a thread continuously running to build the DAG
    '''
    while (True):
        init_buf_len =  len(dag_buffer)
        
        to_remove_from_buffer = []
        
        for buf_ind in range(0, init_buf_len):
            buffer_vertex = dag_buffer[buf_ind]
            flag = True
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
            
        if len(DAG[dag_round]) >= 2*my_node.f +1:
            if dag_round%4==0:
                # handle wave_ready
                pass
                
            dag_round = dag_round +1
            create_new_vertex(dag_round)
            #Rbcast of the vertex.
        
def create_new_vertex(round):
    '''
    Procedure for creating new vertex.It should run as a thread.
    '''
 
    #create vertex for new round here
    if(len(block_to_propose)==0):
        #time.sleep(1)
        block = []
    else:
        block = block_to_propose[0]
        block_to_propose.pop(0)
    
    vertex_id = str(my_node.node_id) + ':' + round
    source = my_node.node_id
    strong_edges = list(DAG[round-1]) 
    #TODO set weak edges
    new_vertex = definitions.Vertex(vertex_id,round, source, block, strong_edges)
    set_weak_edges(new_vertex)
    reliable_bcast(new_vertex)
        
            
        

def r_delivery_to_DAG(vertex):
    if len(vertex.strong_edges) >= 2 * my_node.f + 1:
        dag_buffer.append(vertex) #TODO: check
    
#--------------/DAG Layer-----------------------

#--------------DAGRider-----------------------
decided_wave = 0
delivered_dag_vertices = {}
leader_stack = [] # this is a stack with push, pop functionalities.

def choose_leader(w):
    '''
    selects leader node for the wave w. 
    Need to implement global perfect coin here. 
    '''
    #TODO
    pass
    
def get_wave_vertex_leader(w):
    '''
    Return the leader vertex for wave w.
    param (w) : wave number.
    '''
    leader_node = choose_leader(w)
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
    leader_vertex = get_wave_vertex_leader(w)
    if leader_vertex==None:
        return 
    if not strong_path_from_round4(w, leader_vertex):
        return 
    
    leader_stack.append(leader_vertex)
    for wave_prime in range(w-1,decided_wave, -1):
        leader_vertex_prime = get_wave_vertex_leader(wave_prime)
        if leader_vertex_prime!=None and strong_path(leader_vertex,leader_vertex_prime):
            leader_stack.push(leader_vertex_prime)
            leader_vertex = leader_vertex_prime
    decided_wave = w
    order_vertices(leader_stack)
    
def order_vertices(leader_stack):
    while(len(leader_stack)>0):
        leader_vertex = leader_stack.pop()
        vertices_to_deliver = defaultdict(set)
        for round in range(0, leader_vertex.round):
            for vertex in DAG[round]:
                if(path(leader_vertex, vertex) and vertex not in delivered_dag_vertices):
                    vertices_to_deliver[vertex.round].append(vertex)

    for round in vertices_to_deliver:
        for vertex in vertices_to_deliver[round]:
            # TODO output a_deliver(vertex.block, vertex.round, vertex.source)
            delivered_dag_vertices.append(vertex)
            


#--------------/DAGRider-----------------------


#--------------FLASK ENDPOINT-------------------
@app.route('/pbft', methods=['POST'])
def pbft_endpoint():
    '''
    Receives all the PBFT control messages over POST method and 
    append the messages to the pbft_control_messages queue.
    '''
    try:
        data = request.get_json()
        pbft_control_messages.append(data)
        # Process the control information
        #print(f"Received control information: {data}")
        #print(type(data))

        # You can add your processing logic here

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
        print(f"Request Failed with error {e}")
    

def process_messages():
    '''
    Pops the messages from the pbft_control_messages one by one and process it.
    All the messages here are Reliable Broadcast messages. 
    '''
    
    while(True):
        if pbft_control_messages:
            message = pbft_control_messages.popleft()
            print("Processed message: ", message, type(message))
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
            time.sleep(1)
    
    
def start_flask():
    app.run(host='0.0.0.0', port=pbft_port)
    
if __name__ == '__main__':
    initialize_nodes()
    
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    
    # Create a thread for the traffic monitoring
    traffic_thread = threading.Thread(target=request_rate_track.traffic_rate_tracking)
    traffic_thread.daemon = True
    
    # Create a thread for message processing
    message_processing_thread = threading.Thread(target=process_messages)
    message_processing_thread.daemon = True

    # Start all threads
    flask_thread.start()
    traffic_thread.start()
    message_processing_thread.start()
    
    # Keep the main thread alive
    flask_thread.join()
    traffic_thread.join()
    message_processing_thread.join()
    
    
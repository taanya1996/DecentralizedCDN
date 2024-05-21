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
my_node = definitions.current_node('54.215.43.60', 1, 4, 1)
pbft_control_messages = deque() #these are the reliable broadcast messages. 
# Vertices for the DAGRider is above the reliable Broadcast layer.


def initialize_nodes():
    for i in range(1, my_node.total_nodes+1):
        nodes[i] =  definitions.Node(i, CDN_IPs[i])
            
#--------------RELIABLE BROADCAST SECTION------------------

def reliable_bcast(vertex):
    new_message = definitions.Message()
    message_id = str(my_node.node_id)+str(my_node.next_message_id)
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
        if node.id != my_node.node_id:
            #send INITIAL Messages to all
            http_send_POST(message, node.ip)
            
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
        if node.id != my_node.node_id:
            http_send_POST(new_message, node.ip)
        else:
            #send to self node
            pbft_control_messages.append(new_message)
            

def handle_echo(message):
    message_id = message['id']
    my_node.echo_messages[message_id].add(message)
    
    if len(my_node.echo_messages[message_id]) >= 2 * my_node.f + 1:
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
        if node.id != my_node.node_id:
            http_send_POST(new_message, node.ip)
        else:
            #send to self
            pbft_control_messages.append(new_message)
    my_node.ready_sent_messages.add(message_id)     

def handle_ready(message):
    message_id = message['id']
    my_node.ready_messages[message_id].add(message)
    if len(my_node.ready_messages[message_id]) >= my_node.f +1 :
        #send ready if not already sent ; Ready to Ready Transition:
        if message_id not in my_node.ready_sent_messages:
            broadcast_ready(message)
    
    if len(my_node.ready_messages[message_id]) >= 2 * my_node.f + 1 and message_id not in my_node.delivered_messages:
        deliver_message(message)
        

def deliver_message(message):
    #deliver to the DAG Layer
    pass



#--------------/RELIABLE BROADCAST SECTION------------------

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
        print(f"Received control information: {data}")

        # You can add your processing logic here

        # Return a success response
        return Response(status=200)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


def http_send_POST(message, IP):
    url = 'http://' + IP + '/pbft'
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
            print("Processed message: ", message)
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
    app.run(host='0.0.0.0', port=8080)
    
if __name__ == '__main__':
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
    
    
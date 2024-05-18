from flask import Flask, request, jsonify, Response
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
import subprocess
import threading
import request_rate_track


app = Flask(__name__)
pbft_control_messages = deque()

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


def process_messages():
    '''
    Pops the messages from the pbft_control_messages one by one and process it.
    '''
    
    while(True):
        if pbft_control_messages:
            message = pbft_control_messages.popleft()
            print("Processed message: ", message)
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
    
    
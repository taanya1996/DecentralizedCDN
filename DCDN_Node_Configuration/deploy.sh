#!/bin/bash

# Define your servers and paths
SERVERS=("ec2-54-215-43-60.us-west-1.compute.amazonaws.com" "34.201.142.18" "52.74.244.78" "ec2-18-132-44-229.eu-west-2.compute.amazonaws.com")
USERNAME="ec2-user"
LOCAL_PATH="/Users/taanyanithyaanand/Downloads/DSLab/DecentralizedCDN/DCDN_Node_Configuration"
REMOTE_PATH="/home/ec2-user/gpc/"
SSH_KEY_DIR="/Users/taanyanithyaanand/Downloads/DSLab"
KEYS=("DCDN.pem" "dcdn-us-east-1.pem" "dcdn-ap-southeast-1.pem" "dcdn-eu-west2.pem")

for i in "${!SERVERS[@]}"; do
    SERVER=${SERVERS[$i]}
    KEY=${KEYS[$i]}
    SSH_KEY_PATH="$SSH_KEY_DIR/$KEY"

    echo "Deploying to $SERVER"
    ssh -i $SSH_KEY_PATH $USERNAME@$SERVER "sudo rm -rf $REMOTE_PATH/*"

    scp -i $SSH_KEY_PATH -r $LOCAL_PATH/application.py $USERNAME@$SERVER:$REMOTE_PATH
    scp -i $SSH_KEY_PATH -r $LOCAL_PATH/definitions.py $USERNAME@$SERVER:$REMOTE_PATH
    scp -i $SSH_KEY_PATH -r $LOCAL_PATH/request_rate_track.py $USERNAME@$SERVER:$REMOTE_PATH

    echo "Deployment to $SERVER completed"
done

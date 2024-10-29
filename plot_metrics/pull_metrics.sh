SERVERS=("54.215.43.60" "34.201.142.18" "52.74.244.78" "18.132.44.229")
USERNAME="ec2-user"
LOCAL_PATH="/Users/taanyanithyaanand/Downloads/DSLab/DecentralizedCDN/plot_metrics/"
REMOTE_PATH="/home/ec2-user/gpc/metrics/"
SSH_KEY_DIR="/Users/taanyanithyaanand/Downloads/DSLab"
KEYS=("DCDN.pem" "dcdn-us-east-1.pem" "dcdn-ap-southeast-1.pem" "dcdn-eu-west2.pem")

rm -rf $LOCAL_PATH/metrics
for i in "${!SERVERS[@]}"; do
    SERVER=${SERVERS[$i]}
    KEY=${KEYS[$i]}
    SSH_KEY_PATH="$SSH_KEY_DIR/$KEY"

    echo "Pulling metrics from $SERVER"
    scp -i $SSH_KEY_PATH -r $USERNAME@$SERVER:$REMOTE_PATH $LOCAL_PATH 
    scp -i $SSH_KEY_PATH -r $USERNAME@$SERVER:'/home/ec2-user/*.txt' $LOCAL_PATH/metrics

    echo "Metrics from $SERVER successfully fetched"
done

# Decentralized Content Delivery Network
An attempt to build a reliable Decentralized CDN supporting control information dissemination in a byzantine environment using DAG based Byzantine Atomic Broadcast (BAB) Protocol.

### Description
The project builds a Decentralized CDN with Rate limiting feature. Each node monitors the traffic for Rate Limiting the IPs and this Rate Limiting information is the control information disseminated across all the CDN nodes through [DAGRider Byzantine Atomic Broadcast protocol(1)](#references) to collectively Block/Unblock the IPs as part of Rate Limiting.

### Experimental Setup
- The CDN system of 4 nodes is hosted on AWS EC2 instances
- One origin web server serving the web content using NGINX using the configuration in   
` DecentralizedCDN/origin_server/nginx.conf` 
- Each CDN node is configured as an NGINX reverse proxy using the configuration in    `DecentralizedCDN/DCDN_Node_Configuration/nginx.conf`
- To start the CDN system, run the following commands on the EC2 instances simultaneously   
`sudo python3 application.py`
- To test the performance of the CDN system, run the python test scripts under `Tests` folder
 
This will start the CDN system of 4 nodes, starts the DAGRider BAB protocol and traffic monitoring.

### References
1. Idit Keidar, Eleftherios Kokoris-Kogias, Oded Naor, and Alexander Spiegelman. 2021. All you need is dag. In Proceedings of the 2021 ACM Symposium on Principles of Distributed Computing (PODC).
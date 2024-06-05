import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
import subprocess

def clear_blocklist():
    '''
    Clears the file /etc/nginx/blocked_ips.conf
    '''
    blocklist_file = '/etc/nginx/blocked_ips.conf'
    with open(blocklist_file, 'w') as file:
        file.write("# Blocked IPs\n")
        
    subprocess.run(['nginx', '-s', 'reload'])
    

def parse_line(line):
    """ Parse the log line to extract the IP and the timestamp. """
    fields = line.split(" ")
    ip = fields[0]
    # Extract timestamp, assuming format [day/month/year:hour:minute:second zone]
    timestamp = datetime.strptime(fields[3][1:], '%d/%b/%Y:%H:%M:%S')
    return ip, timestamp

def update_blocklist(blocked_ips):
    """ Update the Nginx blocklist configuration file with the blocked IPs. """
    blocklist_file = '/etc/nginx/blocked_ips.conf'
    print(f'Updated IP Block List: {blocked_ips}')
    with open(blocklist_file, 'w') as file:
        for ip in blocked_ips:
            file.write(f"deny {ip};\n")
    # Reload Nginx to apply the new blocklist
    subprocess.run(['nginx', '-s', 'reload'])
    print('BlockList file updated')

    

def traffic_rate_tracking():
    '''
    The function continously parses the new log entry in the nginx log to track the rate of request from each IP.
    '''
    
    clear_blocklist()
    
    log_file = '/var/log/nginx/access.log'
    request_threshold = 100
    window_duration = timedelta(minutes=5)
    
    windows = defaultdict(deque) #Dictionary with IP as key and deque as values holding the timestamp
    blocked_ips = set()
    
    with open(log_file, 'r') as file:
        file.seek(0,2)
        
        while(True):
            log_line = file.readline()
            if not log_line:
                time.sleep(1)
                continue
            
            ip, timestamp = parse_line(log_line)
            
            while windows[ip] and windows[ip][0] < timestamp - window_duration:
                windows[ip].popleft()
                
            windows[ip].append(timestamp)
            
            #check whether the corresponding IP has exceeded the threshold
            if len(windows[ip]) >= request_threshold:
                if ip not in blocked_ips:
                    blocked_ips.add(ip)
                    update_blocklist(blocked_ips) 
                print(f"Alert: {ip} has made {len(windows[ip])} requests in the last 5 minutes.")
            else:
                if ip in blocked_ips:
                    blocked_ips.remove(ip)
                    update_blocklist(blocked_ips)
                    print(f"Alert: IP {ip} has been removed from blocked list. ", ip)
                    
if __name__ == '__main__':
    traffic_rate_tracking()    
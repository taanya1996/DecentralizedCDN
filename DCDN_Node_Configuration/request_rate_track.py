import time
from collections import defaultdict, deque
from datetime import datetime, timedelta

def parse_line(line):
    """ Parse the log line to extract the IP and the timestamp. """
    fields = line.split(" ")
    ip = fields[0]
    # Extract timestamp, assuming format [day/month/year:hour:minute:second zone]
    timestamp = datetime.strptime(fields[3][1:], '%d/%b/%Y:%H:%M:%S')
    return ip, timestamp

def rate_tracking():
    '''
    The function continously parses the new log entry in the nginx log to track the rate of request from each IP.
    '''
    log_file = '/var/log/nginx/access.log'
    request_threshold = 100
    window_duration = timedelta(minutes=5)
    
    windows = defaultdict(deque) #Dictionary with IP as key and deque as values holding the timestamp
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
                print(f"Alert: {ip} has made {len(windows[ip])} requests in the last 5 minutes.")
                
if __name__ == '__main__':
    rate_tracking()    
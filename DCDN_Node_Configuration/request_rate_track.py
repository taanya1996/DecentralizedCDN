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
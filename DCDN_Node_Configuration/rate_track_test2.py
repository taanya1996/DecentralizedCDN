'''
This script will make a request of 200 in the 1st five min 
Wait for about 5 min and then make another 200 requests in the next 5 min.
'''

import requests
import time
        
def send_requests(target_url, uri_list, total_requests, window_seconds):
    '''
    The function makes a total of 'total_requests' requests within window_seconds 
    The request uri is distributed equally among all the uris in the uri_list
    '''
    interval = window_seconds // total_requests
    ind = 0
    total_uri = len(uri_list)
    for i in range(1, total_requests+1):
        try:
            response = requests.get(target_url+uri_list[ind])
            print(f"Request {i}: Status Code {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Request {i}: Failed with error {e}")
        ind = (ind + 1)%total_uri
        time.sleep(0.5)
    
if __name__ == "__main__":
    target_ips = ['54.215.43.60','34.201.142.18','52.74.244.78','18.132.44.229']
    target_url = "http://13.52.182.233" #CDN Node IP
    uri_list = ['/', '/project_overview', '/problem_statement', '/architecture', '/application_components', '/metrics', '/testing' ]# Replace with your desired endpoint
    request_count = 200  # Number of requests
    window_seconds = 60  # Duration of the window in seconds (5 minutes)

    for ip in target_ips:
        print(f"Targeting IP : {ip}")
        send_requests('http://'+ ip, uri_list, request_count, window_seconds)
        time.sleep(100)
        send_requests('http://'+ ip, uri_list, request_count, window_seconds)

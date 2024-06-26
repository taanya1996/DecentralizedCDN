'''
This script will make a request of 200 in a 5 min window period.
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
        time.sleep(interval)
    
if __name__ == "__main__":
    target_url = "http://3.10.107.156" #CDN Node IP
    uri_list = ['/', '/project_overview', '/problem_statement', '/architecture', '/application_components', '/metrics', '/testing' ]# Replace with your desired endpoint
    request_count = 200  # Number of requests
    window_seconds = 300  # Duration of the window in seconds (5 minutes)

    send_requests(target_url, uri_list, request_count, window_seconds)

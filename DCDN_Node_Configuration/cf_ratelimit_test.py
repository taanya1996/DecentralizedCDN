import requests
import time

def send_requests(target_url, total_requests):
    '''
    The function makes a total of 'total_requests' requests within window_seconds 
    The request uri is distributed equally among all the uris in the uri_list
    '''
    ind = 0
    for i in range(1, total_requests+1):
        try:
            response = requests.get(target_url)
            print(f"{time.asctime()} Request {i}: Status Code {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Request {i}: Failed with error {e}")
        time.sleep(0.5)

if __name__ == "__main__":
    target_url = "https://d1v3u11vzzyd6l.cloudfront.net"
    total_requests = 1000
    send_requests(target_url, total_requests)
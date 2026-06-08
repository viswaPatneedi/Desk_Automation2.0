import requests
import time
import datetime
import json

def get_lightspeed_sat():
    url = "https://sat-stg.codebig2.net/v2/oauth/token"

    headers = {
        'Content-Type': 'application/json',
        'X-Client-Id': 'rdkmwlrqateam',
        'X-Client-Secret': '909a7e838c6a5909601ab94b111b3c92'
    }

    response = requests.request("POST", url, headers=headers, timeout=10)
    print(f"SAT Response Status: {response.status_code}")
    print(f"SAT Response Body: {response.text}")
    return response.json()['access_token']

def send_lightspeed_request(method, endpoint, data=None, files=None):
    url = "https://axiom-lightspeed.rdkops.comcast.net" + endpoint

    headers = {
        'Authorization': 'Bearer ' + get_lightspeed_sat()
    }

    response = requests.request(method, url, headers=headers, data=data, files=files, timeout=60)
    return response


def main():

    data = {
        "ttls":"15",
        "commands":"cat /version.txt",
        "mac_array":"1C:2F:A2:30:35:B6",
        "region":"NA",
        "webpatimeout":60,
        "criteria":"(?s)(.+)",
        "max_macs": 20,
        "slack": "automate-deploy-ops",
        "justification": "Demo Script for Testing"
    }


    response = send_lightspeed_request("POST", "/revstbssh", data=data)
    response.raise_for_status()

    trace_id = response.text.replace('"', '')

    print("Trace ID: " + trace_id)

    waiting_for_job = True
    current_time = datetime.datetime.now()
    timeout_time = current_time + datetime.timedelta(minutes=15)

    while waiting_for_job:

        response = send_lightspeed_request("GET", "/checkStatus?trace_id=" + trace_id)
        if response.status_code == 200:
            result = response.json()
            if (type(result) == dict):
                if result['status'] == 'done':
                    waiting_for_job = False
        if datetime.datetime.now() > timeout_time:
            raise Exception("Timeout waiting For Job")
        
        print("Job not done yet, sleeping for 15 seconds...")
        time.sleep(15)

    response = send_lightspeed_request("POST", "/previewMessage?trace_id=" + trace_id)
    json_results = response.json()
    print(json.dumps(json_results, indent=4))

main()

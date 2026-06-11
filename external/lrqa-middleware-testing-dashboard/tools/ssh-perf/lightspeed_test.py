#!/usr/bin/env python3
"""
Lightspeed RevSSH API Integration Script
Sends commands to devices via Lightspeed RevSSH endpoint
"""

import requests
import time
import json
import sys
from datetime import datetime, timedelta

# ============================================================================
# CONFIGURATION - Replace with your actual credentials
# ============================================================================
CLIENT_ID = 'rdkmwlrqateam'
CLIENT_SECRET = 'b58d6b3146f63ce121257b865743e52a'

# Lightspeed API endpoints
SAT_URL = "https://sat-prod.codebig2.net/v2/oauth/token"
LIGHTSPEED_BASE_URL = "https://axiom-lightspeed.rdkops.comcast.net"
REVSTBSSH_ENDPOINT = LIGHTSPEED_BASE_URL + "/revstbssh"
STATUS_ENDPOINT = LIGHTSPEED_BASE_URL + "/checkStatus"
RESULTS_ENDPOINT = LIGHTSPEED_BASE_URL + "/previewMessage"

# Device details
DEVICE_NAME = "Element-A4K-DESK"
DEVICE_MAC = "1C:2F:A2:30:35:B6"
DEVICE_IP = "10.0.0.250"

# Command to execute
COMMAND = "cat /version.txt"

# ============================================================================
# FUNCTIONS
# ============================================================================

def get_lightspeed_access_token():
    """
    Obtain access token from Lightspeed SAT endpoint
    """
    try:
        headers = {
            'Content-Type': 'application/json',
            'X-Client-Id': CLIENT_ID,
            'X-Client-Secret': CLIENT_SECRET
        }
        
        print(f"[{datetime.now()}] Authenticating with Lightspeed SAT...")
        response = requests.post(SAT_URL, headers=headers, timeout=10)
        response.raise_for_status()
        
        token = response.json()['access_token']
        print(f"[{datetime.now()}] ✓ Authentication successful")
        return token
    
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now()}] ✗ Authentication failed: {e}")
        sys.exit(1)


def send_lightspeed_request(method, endpoint, token, data=None, files=None):
    """
    Send request to Lightspeed API
    """
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.request(
            method, 
            endpoint, 
            headers=headers, 
            data=data, 
            files=files,
            timeout=60
        )
        response.raise_for_status()
        return response
    
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now()}] ✗ Request failed: {e}")
        raise


def execute_command_on_device(token, mac_address, command, device_name):
    """
    Execute command on device via Lightspeed RevSSH
    """
    # Prepare payload
    payload = {
        "ttls": "20",                          # 20 second timeout
        "region": "NA",                        # North America
        "commands": command,                   # Command to execute
        "mac_array": mac_address,              # Device MAC address
        "justification": f"Execute '{command}' on {device_name}",
        "max_macs": "1",                       # Max number of devices to reach
        "criteria": "(?s)(.+)"                # Capture all output
    }
    
    print(f"\n[{datetime.now()}] Submitting RevSSH request...")
    print(f"  Device: {device_name} ({mac_address})")
    print(f"  Command: {command}")
    print(f"  Timeout: 20 seconds")
    print(f"  Region: NA")
    
    response = send_lightspeed_request("POST", REVSTBSSH_ENDPOINT, token, data=payload)
    
    # Extract trace ID
    trace_id = response.text.strip().strip('"')
    print(f"[{datetime.now()}] ✓ Request submitted")
    print(f"  Trace ID: {trace_id}")
    
    return trace_id


def check_job_status(token, trace_id):
    """
    Check status of RevSSH job
    """
    endpoint = f"{STATUS_ENDPOINT}?trace_id={trace_id}"
    response = send_lightspeed_request("GET", endpoint, token)
    return response.json()


def get_job_results(token, trace_id):
    """
    Get results of completed RevSSH job
    """
    endpoint = f"{RESULTS_ENDPOINT}?trace_id={trace_id}"
    response = send_lightspeed_request("POST", endpoint, token)
    return response.json()


def wait_for_job_completion(token, trace_id, max_wait_minutes=5):
    """
    Wait for job to complete and return results
    """
    print(f"\n[{datetime.now()}] Waiting for job completion...")
    
    start_time = datetime.now()
    timeout_time = start_time + timedelta(minutes=max_wait_minutes)
    
    while True:
        # Check current time
        if datetime.now() > timeout_time:
            print(f"[{datetime.now()}] ✗ Timeout: Job did not complete within {max_wait_minutes} minutes")
            return None
        
        try:
            # Check job status
            status_response = check_job_status(token, trace_id)
            
            if isinstance(status_response, dict) and status_response.get('status') == 'done':
                print(f"[{datetime.now()}] ✓ Job completed")
                return get_job_results(token, trace_id)
            
            print(f"[{datetime.now()}] Job status: {status_response.get('status', 'unknown')} - retrying in 10 seconds...")
            time.sleep(10)
        
        except Exception as e:
            print(f"[{datetime.now()}] Error checking status: {e} - retrying in 10 seconds...")
            time.sleep(10)


def display_results(results):
    """
    Display command results in formatted output
    """
    print(f"\n{'='*70}")
    print(f"LIGHTSPEED REVSSH COMMAND RESULTS")
    print(f"{'='*70}")
    print(json.dumps(results, indent=2))
    print(f"{'='*70}\n")


def main():
    """
    Main execution function
    """
    print(f"\n{'='*70}")
    print(f"LIGHTSPEED REVSSH API TEST")
    print(f"{'='*70}")
    print(f"Timestamp: {datetime.now()}")
    
    # Validate credentials
    if CLIENT_ID == '<YOUR_CLIENT_ID>' or CLIENT_SECRET == '<YOUR_CLIENT_SECRET>':
        print("\n✗ ERROR: Please update CLIENT_ID and CLIENT_SECRET in the script!")
        print("   These are required to authenticate with Lightspeed API")
        sys.exit(1)
    
    try:
        # Step 1: Get access token
        token = get_lightspeed_access_token()
        
        # Step 2: Submit command to device
        trace_id = execute_command_on_device(
            token, 
            DEVICE_MAC, 
            COMMAND,
            DEVICE_NAME
        )
        
        # Step 3: Wait for job completion
        results = wait_for_job_completion(token, trace_id, max_wait_minutes=5)
        
        # Step 4: Display results
        if results:
            display_results(results)
            print("✓ Command execution completed successfully\n")
        else:
            print("✗ Failed to retrieve results\n")
    
    except KeyboardInterrupt:
        print("\n[User interrupted] Exiting...\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

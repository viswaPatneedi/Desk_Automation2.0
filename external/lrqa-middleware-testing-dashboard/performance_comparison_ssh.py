#!/usr/bin/env python3
"""
Performance Comparison: Regular SSH vs Lightspeed SSH
This script benchmarks execution time differences between direct SSH (Paramiko) 
and cloud-based Lightspeed SSH service.
"""

import time
import json
import datetime
import requests
import paramiko
import statistics
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict


@dataclass
class PerformanceMetrics:
    """Store performance metrics for each test"""
    method_type: str  # "Regular SSH" or "Lightspeed SSH"
    test_number: int
    total_time: float
    connection_time: float  # Time to establish connection
    command_execution_time: float  # Time to execute command
    result_retrieval_time: float  # Time to retrieve results
    command: str
    status: str  # success or failed
    error_message: str = None


class RegularSSHTester:
    """Test regular SSH performance using Paramiko"""
    
    def __init__(self, device_ip: str, port: int, username: str, password: str):
        self.device_ip = device_ip
        self.port = port
        self.username = username
        self.password = password
    
    def execute_command(self, command: str) -> Tuple[float, float, float, str, bool]:
        """
        Execute command via regular SSH and measure timing
        Returns: (connection_time, execution_time, retrieval_time, output, success)
        """
        try:
            # Measure connection time
            conn_start = time.time()
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                self.device_ip,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=10
            )
            connection_time = time.time() - conn_start
            
            # Measure command execution time
            exec_start = time.time()
            stdin, stdout, stderr = ssh.exec_command(command, timeout=30)
            execution_time = time.time() - exec_start
            
            # Measure result retrieval time
            retrieval_start = time.time()
            output = stdout.read().decode('utf-8', errors='ignore').strip()
            retrieval_time = time.time() - retrieval_start
            
            ssh.close()
            
            return connection_time, execution_time, retrieval_time, output, True
            
        except Exception as e:
            return 0, 0, 0, str(e), False


class LightspeedSSHTester:
    """Test Lightspeed SSH performance"""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://axiom-lightspeed.rdkops.comcast.net"
        self.token_url = "https://sat-stg.codebig2.net/v2/oauth/token"
        self.access_token = None
        self.token_expiry = None
    
    def get_access_token(self) -> bool:
        """Fetch OAuth token for Lightspeed service"""
        try:
            token_start = time.time()
            headers = {
                'Content-Type': 'application/json',
                'X-Client-Id': self.client_id,
                'X-Client-Secret': self.client_secret
            }
            
            response = requests.post(self.token_url, headers=headers, timeout=10)
            token_time = time.time() - token_start
            
            if response.status_code == 200:
                self.access_token = response.json()['access_token']
                self.token_retrieval_time = token_time
                return True
            return False
        except Exception as e:
            print(f"Token retrieval failed: {e}")
            return False
    
    def execute_command(self, command: str, mac_address: str) -> Tuple[float, float, float, str, bool]:
        """
        Execute command via Lightspeed SSH and measure timing
        Returns: (auth_time, execution_time, retrieval_time, output, success)
        """
        try:
            if not self.access_token:
                if not self.get_access_token():
                    return 0, 0, 0, "Authentication failed", False
            
            # Measure auth time (includes token retrieval if needed)
            auth_time = getattr(self, 'token_retrieval_time', 0)
            
            # Measure execution time
            exec_start = time.time()
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            
            data = {
                "ttls": "15",
                "commands": command,
                "mac_array": mac_address,
                "region": "NA",
                "webpatimeout": 60,
                "criteria": "(?s)(.+)",
                "max_macs": 1,
                "slack": "automate-deploy-ops",
                "justification": "Performance Testing"
            }
            
            # Submit job
            submit_start = time.time()
            response = requests.post(
                f"{self.base_url}/revstbssh",
                headers=headers,
                data=data,
                timeout=60
            )
            submit_time = time.time() - submit_start
            
            if response.status_code != 200:
                return auth_time, submit_time, 0, f"Job submission failed: {response.status_code}", False
            
            trace_id = response.text.replace('"', '')
            
            # Poll for job completion
            poll_start = time.time()
            timeout_time = datetime.datetime.now() + datetime.timedelta(minutes=15)
            max_polls = 60  # Max 15 minutes with 15-second intervals
            poll_count = 0
            
            while poll_count < max_polls:
                poll_response = requests.get(
                    f"{self.base_url}/checkStatus?trace_id={trace_id}",
                    headers=headers,
                    timeout=30
                )
                
                if poll_response.status_code == 200:
                    result = poll_response.json()
                    if isinstance(result, dict) and result.get('status') == 'done':
                        break
                
                if datetime.datetime.now() > timeout_time:
                    return auth_time, submit_time, 0, "Job polling timeout", False
                
                time.sleep(15)
                poll_count += 1
            
            poll_time = time.time() - poll_start
            execution_time = submit_time + poll_time
            
            # Retrieve results
            retrieval_start = time.time()
            result_response = requests.post(
                f"{self.base_url}/previewMessage?trace_id={trace_id}",
                headers=headers,
                timeout=30
            )
            retrieval_time = time.time() - retrieval_start
            
            if result_response.status_code == 200:
                output = json.dumps(result_response.json(), indent=2)
                return auth_time, execution_time, retrieval_time, output, True
            else:
                return auth_time, execution_time, retrieval_time, f"Result retrieval failed: {result_response.status_code}", False
                
        except Exception as e:
            return 0, 0, 0, str(e), False


def run_performance_tests(
    device_info: Dict,
    lightspeed_info: Dict,
    command: str = "cat /version.txt",
    num_iterations: int = 5
) -> Dict:
    """
    Run performance comparison tests
    
    Args:
        device_info: Dict with keys {ip, port, username, password}
        lightspeed_info: Dict with keys {client_id, client_secret, mac_address}
        command: Command to execute
        num_iterations: Number of times to run each test
    
    Returns: Dict containing detailed metrics and summary
    """
    
    results = {
        "timestamp": datetime.datetime.now().isoformat(),
        "command": command,
        "num_iterations": num_iterations,
        "regular_ssh_metrics": [],
        "lightspeed_ssh_metrics": [],
        "summary": {}
    }
    
    print(f"\n{'='*80}")
    print(f"SSH Performance Comparison Test")
    print(f"{'='*80}")
    print(f"Command: {command}")
    print(f"Iterations per method: {num_iterations}")
    print(f"{'='*80}\n")
    
    # Test Regular SSH
    print("[1/2] Testing Regular SSH (Paramiko)...")
    print("-" * 80)
    
    regular_tester = RegularSSHTester(
        device_info['ip'],
        device_info['port'],
        device_info['username'],
        device_info['password']
    )
    
    for i in range(num_iterations):
        print(f"  Iteration {i+1}/{num_iterations}...", end=" ", flush=True)
        conn_time, exec_time, retr_time, output, success = regular_tester.execute_command(command)
        
        total_time = conn_time + exec_time + retr_time
        metric = PerformanceMetrics(
            method_type="Regular SSH",
            test_number=i + 1,
            total_time=total_time,
            connection_time=conn_time,
            command_execution_time=exec_time,
            result_retrieval_time=retr_time,
            command=command,
            status="success" if success else "failed",
            error_message=output if not success else None
        )
        results["regular_ssh_metrics"].append(asdict(metric))
        print(f"✓ ({total_time:.2f}s)")
    
    # Test Lightspeed SSH
    print("\n[2/2] Testing Lightspeed SSH...")
    print("-" * 80)
    
    lightspeed_tester = LightspeedSSHTester(
        lightspeed_info['client_id'],
        lightspeed_info['client_secret']
    )
    
    for i in range(num_iterations):
        print(f"  Iteration {i+1}/{num_iterations}...", end=" ", flush=True)
        auth_time, exec_time, retr_time, output, success = lightspeed_tester.execute_command(
            command,
            lightspeed_info['mac_address']
        )
        
        total_time = auth_time + exec_time + retr_time
        metric = PerformanceMetrics(
            method_type="Lightspeed SSH",
            test_number=i + 1,
            total_time=total_time,
            connection_time=auth_time,  # Auth time instead of connection
            command_execution_time=exec_time,
            result_retrieval_time=retr_time,
            command=command,
            status="success" if success else "failed",
            error_message=output if not success else None
        )
        results["lightspeed_ssh_metrics"].append(asdict(metric))
        print(f"✓ ({total_time:.2f}s)")
    
    # Calculate statistics
    regular_times = [m['total_time'] for m in results['regular_ssh_metrics'] if m['status'] == 'success']
    lightspeed_times = [m['total_time'] for m in results['lightspeed_ssh_metrics'] if m['status'] == 'success']
    
    if regular_times and lightspeed_times:
        results["summary"] = {
            "regular_ssh": {
                "success_count": len(regular_times),
                "failed_count": len(results['regular_ssh_metrics']) - len(regular_times),
                "min_time": min(regular_times),
                "max_time": max(regular_times),
                "avg_time": statistics.mean(regular_times),
                "median_time": statistics.median(regular_times),
                "std_dev": statistics.stdev(regular_times) if len(regular_times) > 1 else 0,
                "total_time": sum(regular_times)
            },
            "lightspeed_ssh": {
                "success_count": len(lightspeed_times),
                "failed_count": len(results['lightspeed_ssh_metrics']) - len(lightspeed_times),
                "min_time": min(lightspeed_times),
                "max_time": max(lightspeed_times),
                "avg_time": statistics.mean(lightspeed_times),
                "median_time": statistics.median(lightspeed_times),
                "std_dev": statistics.stdev(lightspeed_times) if len(lightspeed_times) > 1 else 0,
                "total_time": sum(lightspeed_times)
            },
            "comparison": {
                "faster_method": "Regular SSH" if statistics.mean(regular_times) < statistics.mean(lightspeed_times) else "Lightspeed SSH",
                "time_difference_avg": abs(statistics.mean(regular_times) - statistics.mean(lightspeed_times)),
                "performance_ratio": statistics.mean(lightspeed_times) / statistics.mean(regular_times) if regular_times else 0,
                "percent_faster": ((statistics.mean(lightspeed_times) - statistics.mean(regular_times)) / statistics.mean(regular_times) * 100) if regular_times else 0
            }
        }
    
    return results


def print_summary(results: Dict):
    """Print formatted summary of results"""
    
    print(f"\n{'='*80}")
    print("PERFORMANCE TEST SUMMARY")
    print(f"{'='*80}\n")
    
    if "summary" not in results or not results["summary"]:
        print("No successful results to summarize.")
        return
    
    summary = results["summary"]
    
    # Regular SSH Stats
    print("📊 REGULAR SSH (Paramiko) - Direct Connection")
    print("-" * 80)
    reg = summary["regular_ssh"]
    print(f"  Success Rate: {reg['success_count']}/{results['num_iterations']} ({reg['success_count']/results['num_iterations']*100:.1f}%)")
    print(f"  Min Time: {reg['min_time']:.3f}s")
    print(f"  Max Time: {reg['max_time']:.3f}s")
    print(f"  Average Time: {reg['avg_time']:.3f}s")
    print(f"  Median Time: {reg['median_time']:.3f}s")
    print(f"  Std Dev: {reg['std_dev']:.3f}s")
    print(f"  Total Time: {reg['total_time']:.3f}s")
    
    # Lightspeed SSH Stats
    print("\n☁️  LIGHTSPEED SSH - Cloud-Based SSH")
    print("-" * 80)
    ls = summary["lightspeed_ssh"]
    print(f"  Success Rate: {ls['success_count']}/{results['num_iterations']} ({ls['success_count']/results['num_iterations']*100:.1f}%)")
    print(f"  Min Time: {ls['min_time']:.3f}s")
    print(f"  Max Time: {ls['max_time']:.3f}s")
    print(f"  Average Time: {ls['avg_time']:.3f}s")
    print(f"  Median Time: {ls['median_time']:.3f}s")
    print(f"  Std Dev: {ls['std_dev']:.3f}s")
    print(f"  Total Time: {ls['total_time']:.3f}s")
    
    # Comparison
    print("\n⚡ COMPARISON")
    print("-" * 80)
    comp = summary["comparison"]
    time_diff = comp["time_difference_avg"]
    ratio = comp["performance_ratio"]
    percent_diff = comp["percent_faster"]
    
    print(f"  Faster Method: {comp['faster_method']}")
    print(f"  Time Difference (Average): {time_diff:.3f}s")
    print(f"  Performance Ratio: {ratio:.2f}x")
    if percent_diff > 0:
        print(f"  Lightspeed is {abs(percent_diff):.1f}% slower than Regular SSH")
    else:
        print(f"  Lightspeed is {abs(percent_diff):.1f}% faster than Regular SSH")
    
    # Key Insights
    print("\n📈 KEY INSIGHTS")
    print("-" * 80)
    if ratio > 1.5:
        print("  ⚠️  Lightspeed SSH is significantly slower (1.5x+)")
        print("     → Use Regular SSH for real-time/latency-sensitive operations")
        print("     → Use Lightspeed SSH when: firewall restrictions apply, remote access needed")
    elif ratio > 1.1:
        print("  ⚠️  Lightspeed SSH has noticeable overhead (10-50%)")
        print("     → Regular SSH preferable for performance-critical tasks")
    else:
        print("  ✓  Performance is comparable")
    
    print("\n" + "="*80 + "\n")


def main():
    """Main execution function"""
    
    # Configuration: Update these with your actual device/service credentials
    device_info = {
        'ip': '192.168.1.100',  # Replace with actual device IP
        'port': 10022,           # Default SSH port (configure as needed)
        'username': 'root',
        'password': 'password'   # Replace with actual password
    }
    
    lightspeed_info = {
        'client_id': 'your_client_id',
        'client_secret': 'your_client_secret',
        'mac_address': '1C:2F:A2:30:35:B6'  # Device MAC address
    }
    
    test_command = "cat /version.txt"
    num_iterations = 3
    
    print("\n⚠️  BEFORE RUNNING THIS TEST:")
    print("-" * 80)
    print("1. Update device_info with your actual SSH credentials")
    print("2. Update lightspeed_info with your Lightspeed OAuth credentials")
    print("3. Update MAC address and test command as needed")
    print("4. Ensure both the device and Lightspeed service are accessible")
    print("-" * 80)
    
    # Run tests
    results = run_performance_tests(
        device_info,
        lightspeed_info,
        command=test_command,
        num_iterations=num_iterations
    )
    
    # Print summary
    print_summary(results)
    
    # Save results to JSON
    output_file = f"ssh_performance_comparison_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"✓ Results saved to: {output_file}\n")
    
    return results


if __name__ == "__main__":
    main()

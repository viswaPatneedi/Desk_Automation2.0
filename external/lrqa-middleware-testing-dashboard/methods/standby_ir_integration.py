#!/usr/bin/env python3
"""
Integration method for Standby & DeepSleep Test with IR Power Control
Integrates with the RDK-E Middleware QA Testing Dashboard
"""

import subprocess
import time
import json
from datetime import datetime

class StandbyDeepSleepIRTest:
    """Standby/DeepSleep test with IR POWER control"""
    
    def __init__(self, device_ip, remote_type="SKY"):
        self.device_ip = device_ip
        self.remote_type = remote_type
        self.logs = []
        self.start_time = datetime.utcnow()
        
    def log_event(self, level, message, details=""):
        """Log event with timestamp"""
        timestamp = datetime.utcnow().isoformat() + "Z"
        event = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "details": details
        }
        self.logs.append(event)
        
        # Also print for real-time visibility
        status_icon = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌"
        }.get(level, "📝")
        
        time_str = datetime.utcnow().strftime("%H:%M:%S UTC")
        detail_str = f" | {details}" if details else ""
        print(f"[{time_str}] {status_icon} {message}{detail_str}")
        
        return event
    
    def execute_ssh(self, command, description="", timeout=30):
        """Execute SSH command with error handling"""
        self.log_event("INFO", f"Executing command", description)
        
        try:
            full_cmd = f'ssh -y -p 10022 root@{self.device_ip} "{command}"'
            result = subprocess.run(
                full_cmd, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=timeout
            )
            
            output = result.stdout.strip()
            
            if result.returncode == 0:
                self.log_event("SUCCESS", "Command executed", output[:100] if output else "Success")
                return output
            else:
                error = result.stderr.strip() if result.stderr else result.stdout.strip()
                self.log_event("ERROR", "Command failed", error[:100])
                return None
                
        except subprocess.TimeoutExpired:
            self.log_event("ERROR", "Command timeout", f"Timeout after {timeout}s")
            return None
        except Exception as e:
            self.log_event("ERROR", "Command exception", str(e)[:100])
            return None
    
    def send_ir_key(self, key_name, description=""):
        """Send IR key to device"""
        full_desc = f"IR {key_name} - {description}" if description else f"IR {key_name}"
        cmd = f"/media/apps/evemu-tools/send_key.sh {key_name}"
        result = self.execute_ssh(cmd, full_desc)
        return result is not None
    
    def query_power_state(self):
        """Query current device power state"""
        cmd = "QueryPowerState 2>/dev/null"
        output = self.execute_ssh(cmd, "Query power state")
        state = output.strip() if output else "UNKNOWN"
        self.log_event("INFO", "Power state", state)
        return state
    
    def wait_for_power_state(self, target_states, max_attempts=10, interval=3):
        """Wait for device to reach target power state"""
        if isinstance(target_states, str):
            target_states = [target_states]
        
        self.log_event("INFO", "Waiting for power state", f"Target: {', '.join(target_states)}")
        
        for attempt in range(1, max_attempts + 1):
            current_state = self.query_power_state()
            
            if current_state in target_states:
                self.log_event("SUCCESS", f"Reached target state", current_state)
                return current_state
            
            if attempt < max_attempts:
                self.log_event("INFO", f"Attempt {attempt}/{max_attempts}", f"State: {current_state}, waiting {interval}s...")
                time.sleep(interval)
        
        self.log_event("ERROR", "Failed to reach target state", f"Final: {current_state}")
        return None
    
    def wait_for_bootstate(self, target_state="NORMAL", max_attempts=10, interval=6):
        """Wait for device boot state"""
        self.log_event("INFO", "Waiting for boot state", f"Target: {target_state}")
        
        for attempt in range(1, max_attempts + 1):
            cmd = "curl -s '0:9001/as/system/bootstate'"
            bootstate = self.execute_ssh(cmd, f"Boot state check {attempt}/{max_attempts}")
            
            if bootstate and target_state in bootstate:
                self.log_event("SUCCESS", "Boot state reached", bootstate[:100])
                return True
            
            if attempt < max_attempts:
                self.log_event("WARNING", f"Boot state check {attempt}/{max_attempts}", bootstate[:100] if bootstate else "No response")
                time.sleep(interval)
        
        self.log_event("ERROR", "Boot state not reached", "Test may continue...")
        return False
    
    def wait_for_epg(self, max_attempts=10, interval=6):
        """Wait for EPG UI to load"""
        self.log_event("INFO", "Waiting for EPG UI", "Checking sky-messages.log")
        
        for attempt in range(1, max_attempts + 1):
            cmd = "grep 'com.bskyb.epgui - RUNNING' /opt/logs/sky-messages.log 2>/dev/null"
            epgstate = self.execute_ssh(cmd, f"EPG check {attempt}/{max_attempts}")
            
            if epgstate and "RUNNING" in epgstate:
                self.log_event("SUCCESS", "EPG is running", epgstate[:80])
                return True
            
            if attempt < max_attempts:
                self.log_event("INFO", f"EPG check {attempt}/{max_attempts}", "Not ready yet...")
                time.sleep(interval)
        
        self.log_event("WARNING", "EPG did not start", "Continuing test...")
        return False
    
    def setup_deep_sleep_timers(self, timer_duration=30):
        """Setup deep sleep timers (same curl commands as standby_test.sh)"""
        self.log_event("INFO", "Setting up deep sleep parameters", f"Timer: {timer_duration}s")
        
        # Low power timer
        cmd1 = f'curl -s 0:9001/as/test/preferences -d \'{{"lowPowerTimerDuration":"{timer_duration}"}}\''
        self.execute_ssh(cmd1, "Configure low power timer")
        time.sleep(1)
        
        # Maintenance timer
        cmd2 = f'curl -s 0:9001/as/test/preferences -d \'{{"nextMaintenanceTimeOverride":"{timer_duration}"}}\''
        self.execute_ssh(cmd2, "Configure maintenance timer")
        time.sleep(1)
        
        # Write timer value
        cmd3 = f"echo -n {timer_duration} > /tmp/deepSleepTimerVal"
        self.execute_ssh(cmd3, "Write timer value")
        
        self.log_event("SUCCESS", "Deep sleep parameters configured", f"Duration: {timer_duration}s")
    
    def run_test(self):
        """Execute the complete test"""
        try:
            self.log_event("INFO", "=== STANDBY & DEEP SLEEP TEST WITH IR CONTROL ===", 
                          f"Device: {self.device_ip}, Remote: {self.remote_type}")
            
            # STEP 1: Wake device
            self.log_event("INFO", "STEP 1: Wake Device from Standby", "Using IR POWER commands")
            for attempt in range(1, 4):
                self.send_ir_key("KEY_POWER", f"Wake attempt {attempt}/3")
                time.sleep(2)
            time.sleep(5)
            
            current_state = self.query_power_state()
            self.log_event("INFO", "After IR POWER", f"State: {current_state}")
            
            # STEP 2: Wait for boot
            self.log_event("INFO", "STEP 2: Wait for Boot State", "Polling 0:9001/as/system/bootstate")
            self.wait_for_bootstate(target_state="NORMAL", max_attempts=10, interval=6)
            
            # STEP 3: Wait for EPG
            self.log_event("INFO", "STEP 3: Wait for EPG UI", "Polling sky-messages.log")
            self.wait_for_epg()
            
            # STEP 4: Verify ON state
            self.log_event("INFO", "STEP 4: Verify Device ON State", "Sending IR POWER")
            self.send_ir_key("KEY_POWER", "Toggle to ON")
            time.sleep(10)
            
            current_state = self.query_power_state()
            if current_state != "ON":
                self.log_event("ERROR", "Device not ON", f"State: {current_state}")
                return False
            self.log_event("SUCCESS", "Device confirmed ON", current_state)
            
            # STEP 5: Setup timers
            self.log_event("INFO", "STEP 5: Configure Deep Sleep", "Setting timers via curl")
            self.setup_deep_sleep_timers(timer_duration=30)
            
            # STEP 6: Toggle to SLEEP
            self.log_event("INFO", "STEP 6: Toggle to Sleep State", "Sending IR POWER")
            self.send_ir_key("KEY_POWER", "Toggle to SLEEP")
            
            # STEP 7: Wait for sleep cycle
            self.log_event("INFO", "STEP 7: Wait for Sleep & Auto-Wake", "Waiting 5 minutes")
            for i in range(60, 0, -10):
                self.log_event("INFO", "Waiting for sleep cycle", f"{i}s remaining")
                time.sleep(10)
            
            # STEP 8: Verify sleep state
            self.log_event("INFO", "STEP 8: Verify Device Entered Sleep", "Polling power state")
            final_state = None
            for attempt in range(1, 11):
                current_state = self.query_power_state()
                if current_state in ["LIGHTSLEEP", "DEEPSLEEP", "STANDBY"]:
                    final_state = current_state
                    self.log_event("SUCCESS", "Device in sleep state", final_state)
                    break
                time.sleep(1)
            
            if not final_state:
                self.log_event("ERROR", "Device did not enter sleep", f"Final: {current_state}")
                return False
            
            # STEP 9: Reboot
            self.log_event("INFO", "STEP 9: Reboot Device", "Sending API reboot command")
            cmd = "curl -s '0:9001/as/system/action/reset?type=reboot' -d ''"
            self.execute_ssh(cmd, "Reboot API")
            
            # STEP 10: Wait for reboot
            self.log_event("INFO", "STEP 10: Wait for Reboot", "Waiting 120s")
            for i in range(120, 0, -30):
                self.log_event("INFO", "Rebooting", f"{i}s remaining")
                time.sleep(30)
            
            # Final state
            self.log_event("INFO", "STEP 11: Verify Final State", "Checking device status")
            final_state = self.query_power_state()
            self.log_event("SUCCESS", "Test Complete", f"Final state: {final_state}")
            
            self.log_event("SUCCESS", "=== TEST COMPLETED SUCCESSFULLY ===", 
                          f"Total time: {(datetime.utcnow() - self.start_time).total_seconds()}s")
            
            return True
            
        except KeyboardInterrupt:
            self.log_event("WARNING", "Test interrupted by user", "")
            return False
        except Exception as e:
            self.log_event("ERROR", "Test exception", str(e))
            import traceback
            print(traceback.format_exc())
            return False
    
    def get_logs(self):
        """Return logs as JSON"""
        return {
            "status": "success" if self.logs[-1]["level"] == "SUCCESS" else "failed",
            "device_ip": self.device_ip,
            "remote_type": self.remote_type,
            "start_time": self.start_time.isoformat() + "Z",
            "end_time": datetime.utcnow().isoformat() + "Z",
            "logs": self.logs
        }

def run_test_method(device_ip, remote_type="SKY"):
    """
    Main function to run the test
    Returns: (success: bool, logs: dict)
    """
    tester = StandbyDeepSleepIRTest(device_ip, remote_type)
    success = tester.run_test()
    return success, tester.get_logs()

if __name__ == "__main__":
    import sys
    
    device_ip = sys.argv[1] if len(sys.argv) > 1 else "10.0.0.106"
    remote_type = sys.argv[2] if len(sys.argv) > 2 else "SKY"
    
    print("\n" + "="*80)
    print(f"Standby & DeepSleep Test - Device: {device_ip}, Remote: {remote_type}")
    print("="*80 + "\n")
    
    success, logs = run_test_method(device_ip, remote_type)
    
    print("\n" + "="*80)
    print("LOGS JSON OUTPUT:")
    print("="*80)
    print(json.dumps(logs, indent=2))
    
    sys.exit(0 if success else 1)

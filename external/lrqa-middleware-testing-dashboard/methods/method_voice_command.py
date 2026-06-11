"""
Voice Command Method - Execute voice commands via text on RDK device
Uses WPEFramework VoiceControl plugin to send text-based voice commands
Checks only the CURL command response - no screen capture or validation
"""

import paramiko
import json
from methods.method_utils import log_message

def execute_voice_command_process(device_ip, port, username, password, iteration, device_name, voice_text, combined_method_name=None):
    """
    Execute voice command using text transcription
    Checks only the CURL command response for success
    
    Args:
        device_ip: IP address of the device
        port: SSH port
        username: SSH username
        password: SSH password
        iteration: Current iteration number
        device_name: Name of the device
        voice_text: The text to send as voice command
        combined_method_name: Combined method name for folder structure (e.g., "REBOOT-VOICECOMMAND")
    """
    # Use simple print logging instead of app.log_message to avoid thread issues
    def log_msg(message):
        print(message)
        log_message(message)
    
    log_msg(f"\n{'='*80}")
    log_msg(f"🎤 VOICE COMMAND TEST - Iteration {iteration}")
    log_msg(f"Device: {device_name} ({device_ip})")
    log_msg(f"Voice Text: '{voice_text}'")
    log_msg(f"{'='*80}\n")
    
    ssh = None
    
    try:
        # Step 1: Establish SSH Connection
        log_msg("📡 Connecting to device via SSH...")
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=30)
        
        log_msg(f"✅ SSH connection established to {device_ip}")
        
        # Step 2: Send Voice Command via CURL
        log_msg(f"\n🎤 Sending voice command: '{voice_text}'...")
        
        # Escape single quotes in voice_text for shell command
        escaped_text = voice_text.replace("'", "'\\''")
        
        # Construct the curl command
        voice_command = (
            f"curl --header 'Content-Type: application/json' "
            f"--request POST --silent "
            f"-d '{{\"jsonrpc\":\"2.0\",\"id\":\"3\",\"method\":\"org.rdk.VoiceControl.1.voiceSessionByText\",\"params\":{{\"transcription\":\"{escaped_text}\"}}}}' "
            f"http://127.0.0.1:9998/jsonrpc"
        )
        
        log_msg(f"Executing command: {voice_command}")
        
        stdin, stdout, stderr = ssh.exec_command(voice_command, timeout=30)
        response = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        log_msg(f"Response: {response}")
        
        if error:
            log_msg(f"⚠️  Error output: {error}")
        
        # Check CURL response for success
        success = False
        if response:
            try:
                result = json.loads(response)
                # Check if response has result with success flag
                if "result" in result and isinstance(result["result"], dict):
                    if result["result"].get("success") == True:
                        log_msg(f"✅ Voice command executed successfully")
                        log_msg(f"Session ID: {result['result'].get('sessionId', 'N/A')}")
                        success = True
                    else:
                        log_msg(f"❌ Voice command returned success=false")
                elif "error" in result:
                    error_msg = result.get("error", {})
                    log_msg(f"❌ Voice command error: {error_msg}")
                else:
                    log_msg(f"⚠️  Unexpected JSON response: {response}")
            except json.JSONDecodeError:
                log_msg(f"❌ Could not parse JSON response: {response}")
        else:
            log_msg("❌ No response received from voice command")
        
        log_msg(f"\n✅ Voice command test iteration {iteration} completed")
        
    except paramiko.AuthenticationException:
        log_msg("❌ SSH authentication failed")
        return {"iteration": iteration, "success": False, "error": "SSH authentication failed"}
    except paramiko.SSHException as e:
        log_msg(f"❌ SSH error: {str(e)}")
        return {"iteration": iteration, "success": False, "error": f"SSH error: {str(e)}"}
    except Exception as e:
        log_msg(f"❌ Unexpected error: {str(e)}")
        return {"iteration": iteration, "success": False, "error": str(e)}
    finally:
        if ssh:
            ssh.close()
            log_msg("🔌 SSH connection closed")
        
        log_msg(f"{'='*80}\n")
        
        # Return results
        return {"iteration": iteration, "success": success, "logs": []}

import paramiko
import os

def test_sftp_download(device_ip, username, password, remote_file, local_file):
    print(f"Connecting to {device_ip} via SFTP...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(device_ip, username=username, password=password, timeout=30)
        sftp = ssh.open_sftp()
        print(f"Attempting to download {remote_file} to {local_file}...")
        sftp.get(remote_file, local_file)
        sftp.close()
        ssh.close()
        if os.path.exists(local_file) and os.path.getsize(local_file) > 0:
            print(f"SUCCESS: Downloaded {local_file} ({os.path.getsize(local_file)} bytes)")
        else:
            print(f"FAIL: File {local_file} not found or empty after download.")
    except Exception as e:
        print(f"ERROR: SFTP download failed: {e}")
        try:
            ssh.close()
        except:
            pass

if __name__ == "__main__":
    # Fill in your device details and file paths here:
    DEVICE_IP = "10.0.0.126"
    USERNAME = "root"
    PASSWORD = ""
    REMOTE_FILE = "/media/apps/test_logs.tgz"  # Change if your .tgz file has a different name
    LOCAL_FILE = "./test_logs.tgz"
    test_sftp_download(DEVICE_IP, USERNAME, PASSWORD, REMOTE_FILE, LOCAL_FILE)

#!/usr/bin/env python3
"""
USB_DEPLOYMENT_QUICK_START.py

Copy this file to USB and run on NEW R-Pi to auto-deploy LRQA Middleware

Usage (on R-Pi terminal):
  chmod +x USB_DEPLOYMENT_QUICK_START.py
  python3 USB_DEPLOYMENT_QUICK_START.py

Or simply:
  bash rpi4-deploy.sh
"""

import os
import sys
import subprocess
import time
from pathlib import Path

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 50}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}{text}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 50}{Colors.ENDC}\n")

def print_section(text):
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}📋 {text}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{'-' * (len(text) + 2)}{Colors.ENDC}")

def print_step(step_num, text):
    print(f"{Colors.OKGREEN}✓ Step {step_num}: {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKBLUE}ℹ️  {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def run_command(cmd, description=""):
    """Run shell command with error handling"""
    if description:
        print(f"{Colors.OKCYAN}→{Colors.ENDC} {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, "", str(e)

def main():
    print_header("🚀 LRQA MIDDLEWARE - R-Pi 4 DEPLOYMENT")
    
    # Check if running as root
    if os.geteuid() != 0:
        print_warning("This script requires sudo privileges")
        print_info("Running with sudo...")
        os.execvp("sudo", ["sudo", "python3"] + sys.argv)
    
    print_section("CHECKING SYSTEM REQUIREMENTS")
    
    # Check for Docker
    success, stdout, stderr = run_command("which docker", "Checking Docker installation")
    if success:
        print_step(1, "Docker is installed ✓")
    else:
        print_error("Docker not found. Installing...")
        run_command("apt-get update && apt-get install -y docker.io docker-compose", 
                   "Installing Docker")
        print_step(1, "Docker installed ✓")
    
    # Start Docker
    print_step(2, "Starting Docker service")
    run_command("systemctl start docker", "Starting Docker")
    run_command("systemctl enable docker", "Enabling Docker auto-start")
    
    print_section("LOADING APPLICATION IMAGE")
    
    # Find Docker image on USB
    usb_paths = [
        "/media/usb/lrqa-middleware-latest.tar",
        "/media/usb/lrqa-middleware-latest.tar.gz",
        "./lrqa-middleware-latest.tar",
        "./lrqa-middleware-latest.tar.gz"
    ]
    
    image_path = None
    for path in usb_paths:
        if os.path.exists(path):
            image_path = path
            break
    
    if image_path:
        print_step(3, f"Found Docker image: {image_path}")
        print_info(f"File size: {Path(image_path).stat().st_size / (1024**3):.1f}GB")
        
        print_step(4, "Loading Docker image (this may take 2-3 minutes)...")
        success, stdout, stderr = run_command(f"docker load -i {image_path}", 
                                             "Loading image")
        if success:
            print(f"{Colors.OKGREEN}✓ Docker image loaded successfully{Colors.ENDC}")
        else:
            print_error(f"Failed to load image: {stderr}")
            return
    else:
        print_warning("Docker image not found on USB")
        print_info("Available files:")
        os.system("ls -lh /media/usb/ 2>/dev/null || ls -lh ./")
        return
    
    print_section("VERIFYING IMAGE")
    
    print_step(5, "Checking loaded image")
    success, stdout, stderr = run_command("docker images | grep lrqa-middleware",
                                         "Listing Docker images")
    if success and stdout:
        print(f"{Colors.OKGREEN}{stdout}{Colors.ENDC}")
    else:
        print_warning("Image may not have loaded correctly")
    
    print_section("CREATING APPLICATION CONTAINER")
    
    print_step(6, "Launching LRQA Middleware container")
    
    docker_run_cmd = '''
    docker run -d \
      --name=lrqa-middleware \
      --restart=unless-stopped \
      -p 11078:11078 \
      -v /app/data:/app/data \
      -v /app/logs:/app/logs \
      --memory=1g \
      --cpus=2 \
      lrqa-middleware:latest
    '''
    
    success, stdout, stderr = run_command(docker_run_cmd.replace('\n', ''),
                                         "Starting container")
    
    if success:
        container_id = stdout.strip()
        print(f"{Colors.OKGREEN}✓ Container started: {container_id}{Colors.ENDC}")
    else:
        print_error(f"Failed to start container: {stderr}")
        return
    
    # Wait for container to be ready
    time.sleep(3)
    
    print_section("VERIFYING DEPLOYMENT")
    
    print_step(7, "Checking container status")
    run_command("docker ps | grep lrqa-middleware")
    
    print_step(8, "Checking container logs")
    os.system("docker logs lrqa-middleware | tail -20")
    
    print_section("✅ DEPLOYMENT COMPLETE")
    
    print_info("Application is running on: http://localhost:11078")
    print_info("Access from another machine: http://<rpi-ip>:11078")
    
    print("\n" + Colors.BOLD + "📝 Useful Commands:" + Colors.ENDC)
    print(f"  {Colors.OKCYAN}View logs:{Colors.ENDC}          docker logs lrqa-middleware -f")
    print(f"  {Colors.OKCYAN}Stop app:{Colors.ENDC}           docker stop lrqa-middleware")
    print(f"  {Colors.OKCYAN}Start app:{Colors.ENDC}          docker start lrqa-middleware")
    print(f"  {Colors.OKCYAN}Restart app:{Colors.ENDC}        docker restart lrqa-middleware")
    print(f"  {Colors.OKCYAN}Open shell:{Colors.ENDC}         docker exec -it lrqa-middleware /bin/bash")
    print(f"  {Colors.OKCYAN}Check status:{Colors.ENDC}       docker ps")
    
    print(f"\n{Colors.OKGREEN}{Colors.BOLD}🎉 Ready to use!{Colors.ENDC}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_error("\nDeployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)

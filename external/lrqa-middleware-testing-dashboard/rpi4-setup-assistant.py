#!/usr/bin/env python3
"""
LRQA Middleware R-Pi 4 Deployment Assistant
Purpose: Interactive setup wizard and verification for Docker deployment
Usage: python3 rpi4-setup-assistant.py
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Configuration
INSTALL_DIR = "/opt/middleware"
VENV_DIR = f"{INSTALL_DIR}/venv"
LOG_DIR = f"{INSTALL_DIR}/logs"
ENV_FILE = f"{INSTALL_DIR}/.env"
CONTAINER_NAME = "lrqa-middleware"
DOCKER_IMAGE_TAG = "encrypted-latest"

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def print_header(text):
    """Print colored header"""
    print(f"\n{Colors.BLUE}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BLUE}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.BLUE}{'='*80}{Colors.ENDC}\n")

def print_step(step_num, text):
    """Print step indicator"""
    print(f"{Colors.CYAN}[STEP {step_num}] {text}{Colors.ENDC}")

def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.YELLOW}ℹ {text}{Colors.ENDC}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")

def run_command(cmd, show_output=False, check=True):
    """Run shell command and return result"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=not show_output,
            text=True,
            check=check
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, None, str(e)

def check_command_exists(cmd):
    """Check if command exists in system"""
    success, _, _ = run_command(f"which {cmd}", check=False)
    return success

def prompt_yes_no(question):
    """Prompt user for yes/no response"""
    while True:
        response = input(f"{Colors.CYAN}{question} [y/n]: {Colors.ENDC}").lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print_info("Please answer 'y' or 'n'")

def prompt_input(question, default=None):
    """Prompt user for input"""
    if default:
        prompt_text = f"{Colors.CYAN}{question} [{default}]: {Colors.ENDC}"
    else:
        prompt_text = f"{Colors.CYAN}{question}: {Colors.ENDC}"
    
    response = input(prompt_text).strip()
    return response if response else default

# ============================================================================
# SYSTEM CHECKS
# ============================================================================

def check_system():
    """Check system prerequisites"""
    print_step(1, "Checking system requirements")
    
    checks = {
        'Docker': check_command_exists('docker'),
        'sudo': check_command_exists('sudo'),
        'curl': check_command_exists('curl'),
        'Python 3': check_command_exists('python3'),
    }
    
    print()
    for tool, available in checks.items():
        status = f"{Colors.GREEN}✓{Colors.ENDC}" if available else f"{Colors.RED}✗{Colors.ENDC}"
        print(f"  {status} {tool:<15}: {'Available' if available else 'Missing'}")
    
    print()
    if not checks['Docker']:
        print_error("Docker is required but not installed")
        print_info("Run: bash install-docker.sh")
        return False
    
    print_success("All requirements met")
    return True

# ============================================================================
# CONFIGURATION
# ============================================================================

def configure_environment():
    """Configure environment variables"""
    print_step(2, "Configure environment variables")
    
    env_config = {}
    
    print_info("Setting up email configuration (for notifications):")
    env_config['SMTP_HOST'] = prompt_input("SMTP Host", "smtp.gmail.com")
    env_config['SMTP_PORT'] = prompt_input("SMTP Port", "587")
    env_config['SENDER_EMAIL'] = prompt_input("Your email address", "")
    env_config['SENDER_PASSWORD'] = prompt_input("Email app password", "")
    
    print_info("Optional settings:")
    env_config['FLASK_PORT'] = prompt_input("Flask port", "11078")
    env_config['PYARMOR_DEBUG'] = "1" if prompt_yes_no("Enable PyArmor debugging?") else "0"
    
    # Create .env file
    os.makedirs(INSTALL_DIR, exist_ok=True, mode=0o755)
    
    with open(ENV_FILE, 'w') as f:
        f.write("# LRQA Middleware Configuration\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
        f.write("FLASK_ENV=production\n")
        f.write("FLASK_APP=app.py\n")
        f.write("PYTHONUNBUFFERED=1\n")
        f.write("PYTHONDONTWRITEBYTECODE=1\n\n")
        for key, value in env_config.items():
            f.write(f"{key}={value}\n")
    
    os.chmod(ENV_FILE, 0o600)
    print_success(f"Configuration saved to {ENV_FILE}")
    return env_config

# ============================================================================
# DOCKER VERIFICATION
# ============================================================================

def verify_docker():
    """Verify Docker installation and image"""
    print_step(3, "Verify Docker setup")
    
    # Check Docker daemon
    success, _, _ = run_command("docker ps", check=False)
    if not success:
        print_error("Docker daemon is not running")
        print_info("Try: sudo systemctl start docker")
        return False
    
    print_success("Docker daemon is running")
    
    # Check for image
    success, output, _ = run_command("docker images --format '{{.Repository}}:{{.Tag}}'", check=False)
    
    if "lrqa-middleware" in output:
        print_success("Docker image found: lrqa-middleware:encrypted-latest")
        return True
    else:
        print_warning("Docker image not found")
        print_info("Available images:")
        for line in output.split('\n'):
            if line.strip():
                print(f"    {line}")
        return False

# ============================================================================
# APPLICATION DIRECTORIES
# ============================================================================

def setup_directories():
    """Setup application directories"""
    print_step(4, "Setup application directories")
    
    dirs = [
        INSTALL_DIR,
        f"{INSTALL_DIR}/iteration_logs",
        f"{INSTALL_DIR}/screenshots",
        f"{INSTALL_DIR}/device_logs",
        LOG_DIR
    ]
    
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
        os.chmod(directory, 0o755)
        print(f"  {Colors.GREEN}✓{Colors.ENDC} {directory}")
    
    print_success("All directories created")

# ============================================================================
# CONTAINER MANAGEMENT
# ============================================================================

def start_container():
    """Start Docker container"""
    print_step(5, "Start Docker container")
    
    # Stop existing container
    run_command(f"docker stop {CONTAINER_NAME}", check=False)
    run_command(f"docker rm {CONTAINER_NAME}", check=False)
    
    # Start new container
    cmd = f"""
    docker run -d \\
        --name {CONTAINER_NAME} \\
        --restart=unless-stopped \\
        -p 11078:11078 \\
        -v {INSTALL_DIR}/iteration_logs:/app/iteration_logs:rw \\
        -v {INSTALL_DIR}/screenshots:/app/screenshots:rw \\
        -v {INSTALL_DIR}/device_logs:/app/device_logs:rw \\
        --env-file {ENV_FILE} \\
        -e PYTHONUNBUFFERED=1 \\
        --memory=1g \\
        --cpus=2 \\
        lrqa-middleware:{DOCKER_IMAGE_TAG}
    """
    
    success, _, _ = run_command(cmd, check=False)
    
    if success:
        print_success("Container started successfully")
        # Wait for initialization
        import time
        print_info("Waiting for application to initialize...")
        time.sleep(10)
        return True
    else:
        print_error("Failed to start container")
        print_info("Check logs: docker logs " + CONTAINER_NAME)
        return False

# ============================================================================
# HEALTH CHECK
# ============================================================================

def health_check():
    """Check application health"""
    print_step(6, "Health check")
    
    # Check if container is running
    success, output, _ = run_command(f"docker ps -f name={CONTAINER_NAME}", check=False)
    
    if not output or CONTAINER_NAME not in output:
        print_error("Container is not running")
        return False
    
    print_success("Container is running")
    
    # Check container logs
    _, logs, _ = run_command(f"docker logs {CONTAINER_NAME}", check=False)
    
    if "Running on" in logs:
        print_success("Flask application is running")
    else:
        print_warning("Application status unclear, check with: docker logs " + CONTAINER_NAME)
    
    # Try health endpoint
    success, _, _ = run_command("curl -s http://localhost:11078/health", check=False)
    
    if success:
        print_success("Health endpoint responsive")
    else:
        print_warning("Health endpoint not responding yet (may still be initializing)")
    
    return True

# ============================================================================
# SYSTEMD SERVICE
# ============================================================================

def setup_systemd_service():
    """Setup systemd service for auto-start"""
    print_step(7, "Setup systemd service")
    
    if not prompt_yes_no("Setup auto-start on boot?"):
        print_info("Skipping systemd setup")
        return
    
    service_content = f"""[Unit]
Description=LRQA Middleware Docker Service
After=docker.service
Requires=docker.service

[Service]
Type=simple
Restart=unless-stopped
RestartSec=5
ExecStart=/usr/bin/docker start -a {CONTAINER_NAME}
ExecStop=/usr/bin/docker stop {CONTAINER_NAME}
User=root

[Install]
WantedBy=multi-user.target
"""
    
    service_file = "/etc/systemd/system/lrqa-middleware.service"
    
    try:
        with open(service_file, 'w') as f:
            f.write(service_content)
        
        run_command("sudo systemctl daemon-reload")
        run_command("sudo systemctl enable lrqa-middleware.service")
        
        print_success("Systemd service configured")
        print_info("Enable with: sudo systemctl start lrqa-middleware")
    except Exception as e:
        print_error(f"Failed to create service: {e}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main setup wizard"""
    print_header("LRQA Middleware R-Pi 4 Setup Assistant")
    
    try:
        # Run setup steps
        if not check_system():
            return 1
        
        env_config = configure_environment()
        
        if not verify_docker():
            print_warning("Docker image may not be ready yet")
        
        setup_directories()
        
        if not start_container():
            return 1
        
        if not health_check():
            print_warning("Some health checks failed, review logs")
        
        setup_systemd_service()
        
        # Print final summary
        print_header("✓ SETUP COMPLETE")
        
        print(f"{Colors.GREEN}Installation Summary:{Colors.ENDC}")
        print(f"  Application URL:  {Colors.CYAN}http://localhost:11078{Colors.ENDC}")
        print(f"  Data Directory:    {Colors.CYAN}{INSTALL_DIR}{Colors.ENDC}")
        print(f"  Config File:       {Colors.CYAN}{ENV_FILE}{Colors.ENDC}")
        print(f"  Container Name:    {Colors.CYAN}{CONTAINER_NAME}{Colors.ENDC}")
        print()
        
        print(f"{Colors.YELLOW}Quick Management Commands:{Colors.ENDC}")
        print(f"  View logs:   {Colors.CYAN}docker logs -f {CONTAINER_NAME}{Colors.ENDC}")
        print(f"  Stop app:    {Colors.CYAN}docker stop {CONTAINER_NAME}{Colors.ENDC}")
        print(f"  Start app:   {Colors.CYAN}docker start {CONTAINER_NAME}{Colors.ENDC}")
        print(f"  Restart:     {Colors.CYAN}docker restart {CONTAINER_NAME}{Colors.ENDC}")
        print()
        
        print(f"{Colors.GREEN}LRQA Middleware is ready to use!{Colors.ENDC}")
        print()
        
        return 0
        
    except KeyboardInterrupt:
        print_error("\nSetup cancelled by user")
        return 1
    except Exception as e:
        print_error(f"Setup failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

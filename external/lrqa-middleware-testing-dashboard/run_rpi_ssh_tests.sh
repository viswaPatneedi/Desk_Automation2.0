#!/bin/bash

# Multi-R-Pi SSH Connection Test Script Wrapper
# Runs parallel SSH connectivity tests to multiple R-Pi devices

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Print header
print_header() {
    echo -e "\n${BOLD}${BLUE}================================${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}================================${NC}\n"
}

# Print info
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Print success
print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

# Print error
print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if Python 3 is available
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    print_success "Python 3 found at $(which python3)"
}

# Check if required Python packages are available
check_dependencies() {
    print_info "Checking Python dependencies..."
    
    python3 -c "import paramiko" 2>/dev/null
    if [ $? -ne 0 ]; then
        print_error "Missing 'paramiko' package"
        echo -e "${YELLOW}Install with: pip install paramiko${NC}"
        return 1
    fi
    
    python3 -c "import sshtunnel" 2>/dev/null
    if [ $? -ne 0 ]; then
        print_error "Missing 'sshtunnel' package"
        echo -e "${YELLOW}Install with: pip install sshtunnel${NC}"
        return 1
    fi
    
    print_success "All required packages are installed"
    return 0
}

# Run standalone SSH test
run_standalone_test() {
    print_header "Running Standalone SSH Connection Test"
    print_info "Testing raw SSH connectivity to multiple R-Pi devices"
    print_info "This test uses Paramiko SSH library directly"
    
    python3 test_parallel_rpi_ssh.py
}

# Run application integration test
run_app_test() {
    print_header "Running Application Integration Test"
    print_info "Testing via application's GDFRPiShellService"
    print_info "This test uses the same SSH services as the application"
    
    python3 test_app_parallel_rpi_ssh.py
}

# Show help
show_help() {
    cat << EOF
${BOLD}Multi-R-Pi SSH Connection Test Suite${NC}

USAGE:
    $0 [OPTION]

OPTIONS:
    standalone      Run standalone SSH test (Paramiko direct)
    app            Run application integration test (GDFRPiShellService)
    both           Run both tests sequentially
    check          Check Python dependencies only
    help           Show this help message

EXAMPLES:
    $0 standalone       # Test raw SSH to multiple R-Pi devices
    $0 app             # Test via application services
    $0 both            # Run both test suites

WHAT IS TESTED:
    ✓ Simultaneous SSH connections to multiple R-Pi infrastructures
    ✓ DESK R-Pi (10.138.17.42:60201) - Controls lab devices
      - OD-AB device (10.0.0.140)
      - DESK LAB device (10.0.0.28)
    ✓ CELLO R-Pi (10.26.52.60:22) - Controls CELLO device
      - CELLO-SKY device (10.0.0.95)
    ✓ Remote command execution (/version.txt retrieval)
    ✓ Tunnel stability and connection times
    ✓ Parallel operation without conflicts

REQUIREMENTS:
    - Python 3.6+
    - paramiko==3.4.0 (SSH library)
    - sshtunnel (Port forwarding)
    - Direct network access to R-Pi devices

CONFIGURATION:
    Device configurations are read from:
    - Json/devices.json (application database)
    - R-Pi credentials hardcoded in test scripts

EOF
}

# Main execution
main() {
    case "${1:-help}" in
        standalone)
            check_python
            if ! check_dependencies; then
                exit 1
            fi
            run_standalone_test
            ;;
        app)
            check_python
            if ! check_dependencies; then
                exit 1
            fi
            run_app_test
            ;;
        both)
            check_python
            if ! check_dependencies; then
                exit 1
            fi
            run_standalone_test
            echo ""
            sleep 2
            run_app_test
            ;;
        check)
            check_python
            check_dependencies
            ;;
        help)
            show_help
            ;;
        *)
            print_error "Unknown option: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main
main "$@"

#!/usr/bin/env bash

# ============================================================================
# MULTI-R-Pi SSH Testing Suite - Main Menu
# ============================================================================
# Complete test suite for verifying parallel SSH connections to multiple
# R-Pi devices and their controlled downstream devices
#
# DESK R-Pi (10.26.52.60:22) → CELLO-SKY (10.0.0.95)
# LAB R-Pi (10.138.17.42:60201) → DT-XIONE_UK-0D-AB (10.0.0.140)
# ============================================================================

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Screen width
WIDTH=$(tput cols 2>/dev/null || echo 80)

# Helper functions
print_header() {
    echo ""
    printf "%${WIDTH}s\n" | tr ' ' '='
    echo -e "${BOLD}${BLUE}  $1${NC}"
    printf "%${WIDTH}s\n" | tr ' ' '='
    echo ""
}

print_section() {
    echo -e "\n${BOLD}${CYAN}→ $1${NC}\n"
}

print_item() {
    echo -e "   ${GREEN}✓${NC} $1"
}

print_command() {
    echo -e "   ${YELLOW}$${NC} ${BLUE}$1${NC}"
}

show_menu() {
    clear
    
    print_header "MULTI-R-Pi SSH TESTING SUITE"
    
    echo "Testing simultaneous SSH connections to multiple R-Pi devices and"
    echo "their controlled downstream devices."
    echo ""
    
    print_section "Infrastructure Configuration"
    echo "   DESK R-Pi Infrastructure:"
    echo "   ├─ R-Pi IP: 10.26.52.60:22 (lrqa/Viswa123!)"
    echo "   └─ Device: CELLO-SKY (10.0.0.95)"
    echo ""
    echo "   LAB R-Pi Infrastructure:"
    echo "   ├─ R-Pi IP: 10.138.17.42:60201 (pi/Eastcoast...)"
    echo "   └─ Device: DT-XIONE_UK-0D-AB (10.0.0.140)"
    echo ""
    
    print_section "Available Options"
    echo ""
    echo "   ${BOLD}[1]${NC} Run Quick Setup (shows configuration)"
    echo "   ${BOLD}[2]${NC} Run Raw SSH Test (Paramiko direct)"
    echo "   ${BOLD}[3]${NC} Run App Integration Test (GDFRPiShellService)"
    echo "   ${BOLD}[4]${NC} Run Both Tests (complete suite)"
    echo "   ${BOLD}[5]${NC} Check Dependencies"
    echo ""
    echo "   ${BOLD}[6]${NC} View Quick Start Guide"
    echo "   ${BOLD}[7]${NC} View Configuration Reference"
    echo "   ${BOLD}[8]${NC} View Complete Test Guide"
    echo "   ${BOLD}[9]${NC} View Test Summary"
    echo ""
    echo "   ${BOLD}[0]${NC} Exit"
    echo ""
    printf "Select option [0-9]: "
}

run_option() {
    case $1 in
        1)
            print_header "Quick Setup Guide"
            bash QUICK_START_RPI_TEST.sh 2>/dev/null || python3 QUICK_START_RPI_TEST.sh
            ;;
        2)
            print_header "Running Raw SSH Test"
            python3 test_parallel_rpi_ssh.py
            ;;
        3)
            print_header "Running App Integration Test"
            python3 test_app_parallel_rpi_ssh.py
            ;;
        4)
            print_header "Running Both Tests"
            bash run_rpi_ssh_tests.sh both
            ;;
        5)
            print_header "Checking Dependencies"
            bash run_rpi_ssh_tests.sh check
            ;;
        6)
            less QUICK_START_RPI_TEST.sh
            ;;
        7)
            less RPI_SSH_CONFIG_REFERENCE.md
            ;;
        8)
            less MULTI_RPI_SSH_TEST_GUIDE.md
            ;;
        9)
            less MULTI_RPI_SSH_TESTING_SUMMARY.md
            ;;
        0)
            echo ""
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option${NC}"
            sleep 2
            ;;
    esac
    
    echo ""
    echo -e "${YELLOW}Press Enter to continue...${NC}"
    read -r
}

# Main loop
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1

while true; do
    show_menu
    read -r choice
    run_option "$choice"
done

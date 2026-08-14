#!/bin/bash

# ============================================================================
# QUICK START: Multi-R-Pi SSH Connection Testing
# ============================================================================

echo "=========================================="
echo "Multi-R-Pi SSH Connection Testing Setup"
echo "=========================================="
echo ""

# Navigate to application directory
cd /home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard

echo "[1] Checking Python dependencies..."
python3 -c "import paramiko, sshtunnel; print('✓ All packages installed')" 2>/dev/null || {
    echo "✗ Missing dependencies. Installing..."
    pip install paramiko==3.4.0 sshtunnel 2>&1 | tail -3
}

echo ""
echo "[2] Test Scripts Available:"
echo "    • test_parallel_rpi_ssh.py - Raw SSH test (Paramiko direct)"
echo "    • test_app_parallel_rpi_ssh.py - Application integration test"
echo "    • run_rpi_ssh_tests.sh - Full test runner"
echo ""

echo "[3] R-Pi Infrastructure Configuration:"
echo ""
echo "    ┌─ DESK R-Pi (Controls CELLO Devices)"
echo "    │  ├─ IP: 10.26.52.60:22"
echo "    │  ├─ User: lrqa"
echo "    │  └─ Device: CELLO-SKY (10.0.0.95)"
echo "    │"
echo "    └─ LAB R-Pi (Controls Lab Devices)"
echo "       ├─ IP: 10.138.17.42:60201"
echo "       ├─ User: pi"
echo "       └─ Device: DT-XIONE_UK-0D-AB (10.0.0.140)"
echo ""

echo "[4] Quick Commands:"
echo ""
echo "    # Check connectivity only"
echo "    bash run_rpi_ssh_tests.sh check"
echo ""
echo "    # Run raw SSH test"
echo "    python3 test_parallel_rpi_ssh.py"
echo ""
echo "    # Run application integration test"
echo "    python3 test_app_parallel_rpi_ssh.py"
echo ""
echo "    # Run both tests"
echo "    bash run_rpi_ssh_tests.sh both"
echo ""

echo "[5] What Gets Tested:"
echo "    ✓ Parallel SSH connections to 2 R-Pi devices"
echo "    ✓ DESK R-Pi (10.26.52.60:22) - CELLO infrastructure"
echo "    ✓ LAB R-Pi (10.138.17.42:60201) - Lab infrastructure"
echo "    ✓ Remote device access via tunnels"
echo "    ✓ Command execution (/version.txt retrieval)"
echo "    ✓ Connection timing and stability"
echo ""

echo "[6] Network Topology Diagram:"
echo ""
echo "    Your Server"
echo "    (10.0.0.x)"
echo "         │"
echo "    ┌────┴──────────────────────┐"
echo "    │                           │"
echo "    │                           │"
echo "  DESK R-Pi                  LAB R-Pi"
echo "  10.26.52.60:22          10.138.17.42:60201"
echo "  (lrqa/Viswa123!)        (pi/Eastcoast...)"
echo "    │                          │"
echo "  CELLO-SKY              DT-XIONE_UK-0D-AB"
echo "  10.0.0.95               10.0.0.140"
echo ""

echo "[7] Expected Output:"
echo "    Success Rate: 100% - ALL TESTS PASSED ✓"
echo "    Total Tests: 2"
echo "    Total Devices Tested: 2"
echo "    Average Connection Time: 2-4 seconds"
echo ""

echo "=========================================="
echo "Ready to test! Run: bash run_rpi_ssh_tests.sh both"
echo "=========================================="

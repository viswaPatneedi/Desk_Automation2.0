#!/bin/bash
# Diagnostic script to check device logs

DEVICE_IP="10.0.0.209"
REBOOT_TIME="2026-01-28 00:45:10"

echo "=== Checking HOME logs on device $DEVICE_IP ==="
echo ""
echo "Reboot time: $REBOOT_TIME"
echo ""
echo "=== ALL HOME logs in sky-messages.log ==="
ssh -p 10022 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@$DEVICE_IP \
  "cat /opt/logs/sky-messages.log | grep -i 'HOME_TILES.*complete'" 2>/dev/null || echo "No logs found"

echo ""
echo "=== Checking log file modification time ==="
ssh -p 10022 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@$DEVICE_IP \
  "ls -lh /opt/logs/sky-messages.log" 2>/dev/null || echo "File not found"

echo ""
echo "=== Last 10 lines of sky-messages.log ==="
ssh -p 10022 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@$DEVICE_IP \
  "tail -10 /opt/logs/sky-messages.log" 2>/dev/null || echo "Cannot read file"

echo ""
echo "=== Log rotation/truncation check ==="
ssh -p 10022 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@$DEVICE_IP \
  "cat /opt/logs/sky-messages.log | wc -l" 2>/dev/null || echo "Cannot count lines"

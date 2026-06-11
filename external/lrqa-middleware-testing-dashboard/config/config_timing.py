"""
Timing Configuration for Device Operations
"""

# Timing settings (in seconds)
wait_for_bootime = 100  # Wait time for device to boot after reboot
wait_before_retry = 10  # Wait time between SSH retry attempts
total_timeout = 300     # Total timeout for waiting for device to come online
wait_after_reboot = 15  # Wait time after device comes online to check logs
wait_for_deepsleep = 60  # Wait time for device to enter deep sleep
wait_after_wakeup = 20   # Wait time after sending IR wake command
wait_for_logs = 15       # Wait time for logs to populate after wake up

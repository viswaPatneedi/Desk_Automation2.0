"""
Device Commands Configuration
"""

# Device control commands
device_status_command = "QueryPowerState\n"
reboot_command = "systemctl reboot\n"
deepsleep_command = "curl -s -X POST http://127.0.0.1:9001/as/test/preferences -d '{\"lowPowerTimerDuration\": \"30\"}'"
power_key_command = "keySimulator -ktvpower"
home_key_command = "keySimulator -khome"
enter_key_command = "keySimulator -kenter"
down_key_command = "keySimulator -kdown"
right_key_command = "keySimulator -kright"
left_key_command = "keySimulator -kleft"
up_key_command = "keySimulator -kup"
hard_power_off_command = "echo 1 > /proc/sys/kernel/sysrq; echo b > /proc/sysrq-trigger"

# Maintenance Manager commands (RDK JSONRPCs)
maintenance_get_status_command = 'curl --header "Content-Type: application/json" --request POST --silent -d \'{"jsonrpc":"2.0","id":"3","method":"org.rdk.MaintenanceManager.1.getMaintenanceActivityStatus","params":{}}\' http://127.0.0.1:9998/jsonrpc'
maintenance_start_command = 'curl --header "Content-Type: application/json" --request POST --silent -d \'{"jsonrpc":"2.0","id":"3","method":"org.rdk.MaintenanceManager.1.startMaintenance","params":{}}\' http://127.0.0.1:9998/jsonrpc'
maintenance_stop_command = 'curl --header "Content-Type: application/json" --request POST --silent -d \'{"jsonrpc":"2.0","id":"3","method":"org.rdk.MaintenanceManager.1.stopMaintenance","params":{}}\' http://127.0.0.1:9998/jsonrpc'
maintenance_reboot_command = 'curl -d \'{"jsonrpc":"2.0","id":42,"method":"org.rdk.System.reboot","params":{"rebootReason":"MAINTENANCE_REBOOT"}}\' http://127.0.0.1:9998/jsonrpc'
# Available methods list for API endpoint
AVAILABLE_METHODS = [
    'reboot',
    'reboot_perf_v2_optimized',
    'trail_method',
    'soft_hard_boot',
    'deepsleep',
    'deepsleep_maintenance_wakeup',
    'maintenance_deepsleep_wakeup',
    'maintenance_CURL_deepsleep_wakeup',
    'power_key',
    'status',
    'ir_test',
    'voice_command',
    'send_remote_keys',
    'screen_validation',
    'xumo_activation',
    'capture_base_image',
    'capture_current_screen',
    'navigate_inputs_xumo',
    'wait',
    'memcapture_tool',
    'execute_command',
    'collect_device_logs',
    'validate_results',
    'activate_flux',
    'navigate_to_tiles',
    'execute_sequence'
]
"""
R-Pi Connection Manager Service
Handles deduplication and grouping of R-Pi connections for multiple devices
Establishes single SSH connection per unique R-Pi configuration
"""

import hashlib
import json
import threading
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

class R_PiConnectionGroupManager:
    """
    Manages R-Pi connections by grouping devices that share the same R-Pi.
    Pre-establishes connections before execution begins.
    """
    
    def __init__(self):
        self.rpi_connection_pool = {}  # {rpi_connection_key: rpi_service_instance}
        self.device_to_rpi_mapping = {}  # {device_ip: rpi_connection_key}
        self.rpi_configs = {}  # {rpi_connection_key: rpi_config_dict}
        self.lock = threading.Lock()
    
    def generate_rpi_key(self, rpi_config: dict) -> str:
        """
        Generate unique key for R-Pi configuration.
        Same R-Pi config (same IP + port + credentials) = same key
        """
        if not rpi_config:
            return None
        
        key_string = f"{rpi_config.get('rpi_ip')}:{rpi_config.get('rpi_port')}:{rpi_config.get('rpi_username')}"
        return hashlib.md5(key_string.encode()).hexdigest()[:12]
    
    def collect_rpi_configs_from_devices(self, devices: List) -> Dict[str, dict]:
        """
        Collect R-Pi configurations from all selected devices.
        
        Args:
            devices: List of Device objects
        
        Returns:
            {rpi_key: rpi_config} dictionary with deduplicated configs
        
        Example:
            devices = [
                Device(ip="10.0.0.140", rpi_config={"rpi_ip": "10.138.17.42", ...}),
                Device(ip="10.0.0.28",  rpi_config={"rpi_ip": "10.138.17.42", ...}),  # Same R-Pi
                Device(ip="10.0.0.X",   rpi_config={"rpi_ip": "10.138.17.50", ...})   # Different R-Pi
            ]
            
            Result:
            {
                "abc123def456": {"rpi_ip": "10.138.17.42", "rpi_port": 60201, ...},
                "xyz789abc123": {"rpi_ip": "10.138.17.50", "rpi_port": 60201, ...}
            }
        """
        unique_rpi_configs = {}
        
        for device in devices:
            if not hasattr(device, 'rpi_config') or not device.rpi_config:
                print(f"⚠️  Device {device.name} ({device.ip}) has no R-Pi config, skipping")
                continue
            
            rpi_config = device.rpi_config
            rpi_key = self.generate_rpi_key(rpi_config)
            
            # Store unique R-Pi config
            if rpi_key not in unique_rpi_configs:
                unique_rpi_configs[rpi_key] = rpi_config
                print(f"✅ Collected R-Pi config: {rpi_key} → {rpi_config.get('rpi_ip')}:{rpi_config.get('rpi_port')}")
            else:
                print(f"ℹ️  R-Pi config already collected: {rpi_key} (device {device.name} uses same R-Pi)")
        
        return unique_rpi_configs
    
    def map_devices_to_rpi(self, devices: List, unique_rpi_configs: Dict[str, dict]) -> Dict[str, List]:
        """
        Map devices to their R-Pi connection keys.
        
        Returns:
            {rpi_key: [device_ip1, device_ip2, ...]} mapping
        
        Example:
            {
                "abc123def456": ["10.0.0.140", "10.0.0.28"],  # 2 DESK devices on same R-Pi
                "xyz789abc123": ["10.0.0.X", "10.0.0.Y"]       # 2 LAB devices on same R-Pi
            }
        """
        rpi_to_devices = {}
        
        for device in devices:
            if not hasattr(device, 'rpi_config') or not device.rpi_config:
                continue
            
            rpi_key = self.generate_rpi_key(device.rpi_config)
            
            if rpi_key not in rpi_to_devices:
                rpi_to_devices[rpi_key] = []
            
            rpi_to_devices[rpi_key].append({
                'ip': device.ip,
                'name': device.name,
                'location': getattr(device, 'location', 'Unknown')
            })
        
        return rpi_to_devices
    
    def establish_rpi_connections(self, unique_rpi_configs: Dict[str, dict]) -> Dict[str, Tuple[bool, str, object]]:
        """
        Establish SSH connections to all unique R-Pi instances.
        This happens before device execution begins.
        
        Args:
            unique_rpi_configs: {rpi_key: rpi_config} from collect_rpi_configs_from_devices()
        
        Returns:
            {rpi_key: (success, message, rpi_service)} for each R-Pi
        
        Example Return:
            {
                "abc123def456": (True, "Connected to R-Pi at 10.138.17.42", <RPiService>),
                "xyz789abc123": (False, "Failed to connect: timeout", None)
            }
        """
        connection_results = {}
        
        for rpi_key, rpi_config in unique_rpi_configs.items():
            rpi_ip = rpi_config.get('rpi_ip')
            rpi_port = rpi_config.get('rpi_port')
            rpi_username = rpi_config.get('rpi_username')
            
            print(f"\n🔌 [R-Pi Connection] Attempting to connect to R-Pi: {rpi_ip}:{rpi_port}")
            
            try:
                # Import here to avoid circular imports
                from services.gdf_rpi_direct_shell_service import GDFRPiDirectShellService
                
                rpi_service = GDFRPiDirectShellService(rpi_config=rpi_config, device_identifier=f"R-Pi-{rpi_key}")
                
                # Establish connection
                success, connect_message = rpi_service.connect()
                
                if success:
                    message = f"✅ Successfully connected to R-Pi at {rpi_ip}:{rpi_port}"
                    print(message)
                    connection_results[rpi_key] = (True, message, rpi_service)
                    
                    # Store in pool for reuse
                    with self.lock:
                        self.rpi_connection_pool[rpi_key] = rpi_service
                        self.rpi_configs[rpi_key] = rpi_config
                else:
                    message = f"❌ Failed to connect to R-Pi at {rpi_ip}:{rpi_port}: {connect_message}"
                    print(message)
                    connection_results[rpi_key] = (False, message, None)
            
            except Exception as e:
                message = f"❌ Error connecting to R-Pi at {rpi_ip}:{rpi_port}: {str(e)}"
                print(message)
                connection_results[rpi_key] = (False, message, None)
        
        return connection_results
    
    def prepare_execution_with_rpi_grouping(self, devices: List) -> Dict:
        """
        Main orchestration function: Collect R-Pi configs, deduplicate, and establish connections.
        
        This should be called BEFORE starting method execution on any device.
        
        Args:
            devices: List of Device objects to execute on
        
        Returns:
            {
                'success': True/False,
                'unique_rpi_count': int,
                'device_to_rpi_mapping': {device_ip: rpi_key},
                'rpi_to_devices_mapping': {rpi_key: [device_info...]},
                'rpi_connection_status': {rpi_key: (success, message, rpi_service)},
                'rpi_connection_pool': {rpi_key: rpi_service},
                'failed_rpi_keys': [rpi_key1, rpi_key2, ...],
                'message': 'Summary message'
            }
        """
        print("\n" + "="*70)
        print("🚀 [R-Pi Connection Manager] Preparing execution with R-Pi grouping")
        print("="*70)
        
        # Step 1: Collect unique R-Pi configurations
        print(f"\n📋 Step 1: Collecting R-Pi configurations from {len(devices)} devices...")
        unique_rpi_configs = self.collect_rpi_configs_from_devices(devices)
        
        if not unique_rpi_configs:
            message = "❌ No R-Pi configurations found in selected devices"
            print(message)
            return {
                'success': False,
                'message': message,
                'unique_rpi_count': 0
            }
        
        print(f"✅ Found {len(unique_rpi_configs)} unique R-Pi configuration(s)")
        
        # Step 2: Map devices to R-Pi keys
        print(f"\n📊 Step 2: Mapping devices to their R-Pi instances...")
        rpi_to_devices_mapping = self.map_devices_to_rpi(devices, unique_rpi_configs)
        
        for rpi_key, devices_list in rpi_to_devices_mapping.items():
            rpi_ip = unique_rpi_configs[rpi_key].get('rpi_ip')
            print(f"  • R-Pi {rpi_ip} [{rpi_key}]: {len(devices_list)} device(s)")
            for dev in devices_list:
                print(f"     - {dev['name']} ({dev['ip']}) [{dev['location']}]")
        
        # Step 3: Establish connections to all unique R-Pi instances
        print(f"\n🔌 Step 3: Establishing SSH connections to {len(unique_rpi_configs)} R-Pi instance(s)...")
        connection_results = self.establish_rpi_connections(unique_rpi_configs)
        
        # Step 4: Check for failures
        failed_rpi_keys = []
        successful_rpi_keys = []
        
        for rpi_key, (success, message, rpi_service) in connection_results.items():
            if success:
                successful_rpi_keys.append(rpi_key)
            else:
                failed_rpi_keys.append(rpi_key)
        
        print(f"\n✅ Successfully connected to {len(successful_rpi_keys)}/{len(unique_rpi_configs)} R-Pi instances")
        
        if failed_rpi_keys:
            print(f"❌ Failed to connect to {len(failed_rpi_keys)} R-Pi instance(s)")
            for rpi_key in failed_rpi_keys:
                print(f"   - {connection_results[rpi_key][1]}")
        
        # Step 5: Create device to R-Pi mapping
        device_to_rpi_mapping = {}
        for device in devices:
            if hasattr(device, 'rpi_config') and device.rpi_config:
                rpi_key = self.generate_rpi_key(device.rpi_config)
                device_to_rpi_mapping[device.ip] = rpi_key
        
        # Determine overall success
        overall_success = len(failed_rpi_keys) == 0
        
        print("\n" + "="*70)
        print(f"📌 Summary: R-Pi grouping preparation {'✅ COMPLETE' if overall_success else '⚠️  PARTIAL'}")
        print("="*70 + "\n")
        
        return {
            'success': overall_success,
            'unique_rpi_count': len(unique_rpi_configs),
            'device_to_rpi_mapping': device_to_rpi_mapping,
            'rpi_to_devices_mapping': rpi_to_devices_mapping,
            'rpi_connection_status': connection_results,
            'rpi_connection_pool': self.rpi_connection_pool,
            'failed_rpi_keys': failed_rpi_keys,
            'message': f"R-Pi connections ready: {len(successful_rpi_keys)} online, {len(failed_rpi_keys)} failed"
        }
    
    def get_rpi_service_for_device(self, device_ip: str) -> Optional[object]:
        """Get the R-Pi service instance for a specific device"""
        rpi_key = self.device_to_rpi_mapping.get(device_ip)
        if rpi_key:
            return self.rpi_connection_pool.get(rpi_key)
        return None
    
    def cleanup(self):
        """Close all R-Pi connections"""
        with self.lock:
            for rpi_key, rpi_service in self.rpi_connection_pool.items():
                try:
                    if hasattr(rpi_service, 'close'):
                        rpi_service.close()
                    print(f"✅ Closed R-Pi connection: {rpi_key}")
                except Exception as e:
                    print(f"⚠️  Error closing R-Pi connection {rpi_key}: {str(e)}")
            
            self.rpi_connection_pool.clear()
            self.device_to_rpi_mapping.clear()
            self.rpi_configs.clear()


# Global instance for singleton pattern
_rpi_connection_manager = None

def get_rpi_connection_manager() -> R_PiConnectionGroupManager:
    """
    Get or create the global R-Pi connection manager instance
    """
    global _rpi_connection_manager
    if _rpi_connection_manager is None:
        _rpi_connection_manager = R_PiConnectionGroupManager()
    return _rpi_connection_manager

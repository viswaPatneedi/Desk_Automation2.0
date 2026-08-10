"""
Tunnel Group Coordinator - Groups devices by R-Pi config for optimal parallel execution
Enables devices sharing same R-Pi backend to execute in parallel using single shared tunnel
"""

import threading
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class TunnelGroup:
    """
    Represents a group of devices sharing the same R-Pi backend
    All devices in group share ONE tunnel for parallel execution
    """
    
    def __init__(self, rpi_ip: str, group_id: str):
        self.rpi_ip = rpi_ip
        self.group_id = group_id
        self.devices: List[Dict] = []
        self.tunnel_service = None
        self.lock = threading.RLock()
        self.created_at = datetime.now()
        self.tunnel_acquired_at = None
        self.is_tunnel_established = False
    
    def add_device(self, device_name: str, device_ip: str, device_obj):
        """Add device to this group"""
        self.devices.append({
            'name': device_name,
            'ip': device_ip,
            'object': device_obj,
            'status': 'pending'
        })
    
    def get_device_count(self) -> int:
        """Get number of devices in group"""
        return len(self.devices)
    
    def __repr__(self):
        device_names = ', '.join([d['name'] for d in self.devices])
        return f"TunnelGroup(R-Pi: {self.rpi_ip}, Devices: [{device_names}])"


class TunnelGroupCoordinator:
    """
    Coordinates tunnel access for groups of devices
    Groups devices by R-Pi config to enable parallel execution
    
    Problem:
    - Sequential tunneling: Device A uses tunnel, Device B waits
    - Not optimal: If Device A & B use same R-Pi, they could share tunnel
    
    Solution:
    - Group devices by R-Pi config upfront
    - Each group gets ONE tunnel (shared by all devices in group)
    - Groups with different R-Pis execute independently
    - Devices within group execute in parallel
    
    Example:
    4 devices triggered simultaneously:
    - Device A: R-Pi 10.138.17.42
    - Device B: R-Pi 10.138.17.42 (same as A)
    - Device C: R-Pi 10.138.17.43
    - Device D: R-Pi 10.138.17.43 (same as C)
    
    Groups created:
    - Group 1: [A, B] → Tunnel to 10.138.17.42
    - Group 2: [C, D] → Tunnel to 10.138.17.43
    
    Execution:
    - A & B execute in parallel (sharing tunnel 1)
    - C & D execute in parallel (sharing tunnel 2)
    - Both groups execute simultaneously (different R-Pis)
    
    Result: All 4 devices execute in parallel instead of sequential!
    """
    
    def __init__(self):
        self.groups: Dict[str, TunnelGroup] = {}  # Key: rpi_ip
        self.lock = threading.RLock()
        self.group_tunnel_locks: Dict[str, threading.RLock] = {}  # Per-group locks
        print("[TUNNEL-GROUP-COORD] Tunnel Group Coordinator initialized")
    
    def analyze_and_group_devices(self, devices: List) -> Dict[str, TunnelGroup]:
        """
        Analyze devices and group them by R-Pi configuration
        
        Args:
            devices: List of Device objects to execute on
            
        Returns:
            Dict mapping R-Pi IP to TunnelGroup with devices
        
        Example:
            devices = [DeviceA (R-Pi: 10.138.17.42), 
                      DeviceB (R-Pi: 10.138.17.42),
                      DeviceC (R-Pi: 10.138.17.43)]
            
            groups = coordinator.analyze_and_group_devices(devices)
            # Returns:
            # {
            #     '10.138.17.42': TunnelGroup([DeviceA, DeviceB]),
            #     '10.138.17.43': TunnelGroup([DeviceC])
            # }
        """
        with self.lock:
            self.groups = {}  # Reset groups
            
            print(f"[TUNNEL-GROUP-COORD] Analyzing {len(devices)} devices for R-Pi grouping...")
            
            for device in devices:
                # Skip non-RACK devices
                if not device.is_rack_device:
                    print(f"[TUNNEL-GROUP-COORD]   • {device.name}: DESK device (no tunnel needed)")
                    continue
                
                # Get R-Pi IP from config
                if not device.rpi_config:
                    print(f"[TUNNEL-GROUP-COORD]   ⚠️  {device.name}: No R-Pi config")
                    continue
                
                rpi_ip = device.rpi_config.get('rpi_ip')
                if not rpi_ip:
                    print(f"[TUNNEL-GROUP-COORD]   ⚠️  {device.name}: No R-Pi IP in config")
                    continue
                
                # Create group if doesn't exist
                if rpi_ip not in self.groups:
                    group_id = f"group_{rpi_ip.replace('.', '_')}"
                    self.groups[rpi_ip] = TunnelGroup(rpi_ip, group_id)
                    # Create per-group lock
                    self.group_tunnel_locks[rpi_ip] = threading.RLock()
                    print(f"[TUNNEL-GROUP-COORD]   ✨ Created group for R-Pi {rpi_ip}")
                
                # Add device to group
                self.groups[rpi_ip].add_device(device.name, device.ip, device)
                print(f"[TUNNEL-GROUP-COORD]     ✓ Added {device.name} to group")
            
            # Print summary
            print(f"\n[TUNNEL-GROUP-COORD] Grouping Summary:")
            print(f"[TUNNEL-GROUP-COORD] ├─ Total groups: {len(self.groups)}")
            for rpi_ip, group in self.groups.items():
                print(f"[TUNNEL-GROUP-COORD] ├─ R-Pi {rpi_ip}: {group.get_device_count()} devices")
                for device in group.devices:
                    print(f"[TUNNEL-GROUP-COORD] │  └─ {device['name']}")
            print()
            
            return self.groups
    
    def acquire_tunnel_for_group(self, rpi_ip: str, timeout: int = 60) -> Tuple[bool, str]:
        """
        Acquire tunnel for a specific R-Pi group
        All devices in group will share this tunnel
        
        Args:
            rpi_ip: R-Pi IP address (group identifier)
            timeout: Max seconds to wait for tunnel availability
            
        Returns:
            Tuple of (success, message)
        """
        if rpi_ip not in self.groups:
            return False, f"No group found for R-Pi {rpi_ip}"
        
        group = self.groups[rpi_ip]
        group_lock = self.group_tunnel_locks.get(rpi_ip)
        
        if not group_lock:
            return False, f"No lock for group {rpi_ip}"
        
        # Try to acquire group lock with timeout
        acquired = group_lock.acquire(blocking=True, timeout=timeout)
        
        if acquired:
            group.tunnel_acquired_at = datetime.now()
            device_names = ', '.join([d['name'] for d in group.devices])
            msg = f"[TUNNEL-GROUP-COORD] ✅ Tunnel acquired for group {rpi_ip}: [{device_names}]"
            print(msg)
            return True, msg
        else:
            device_names = ', '.join([d['name'] for d in group.devices])
            msg = f"[TUNNEL-GROUP-COORD] ❌ Timeout acquiring tunnel for group {rpi_ip}: [{device_names}]"
            print(msg)
            return False, msg
    
    def release_tunnel_for_group(self, rpi_ip: str):
        """
        Release tunnel for a specific R-Pi group
        Allows other groups/jobs to use this R-Pi
        
        Args:
            rpi_ip: R-Pi IP address (group identifier)
        """
        if rpi_ip not in self.groups:
            return
        
        group = self.groups[rpi_ip]
        group_lock = self.group_tunnel_locks.get(rpi_ip)
        
        if not group_lock:
            return
        
        try:
            group_lock.release()
            duration = (datetime.now() - group.tunnel_acquired_at).total_seconds() if group.tunnel_acquired_at else 0
            device_names = ', '.join([d['name'] for d in group.devices])
            msg = f"[TUNNEL-GROUP-COORD] ✅ Tunnel released for group {rpi_ip}: [{device_names}] (held {duration:.1f}s)"
            print(msg)
        except RuntimeError:
            msg = f"[TUNNEL-GROUP-COORD] ⚠️  Lock not held for group {rpi_ip}"
            print(msg)
    
    def get_group_for_device(self, device_ip: str) -> Optional[TunnelGroup]:
        """
        Get the tunnel group that contains a specific device
        
        Args:
            device_ip: Device IP address
            
        Returns:
            TunnelGroup if found, None otherwise
        """
        for group in self.groups.values():
            for device in group.devices:
                if device['ip'] == device_ip:
                    return group
        return None
    
    def get_devices_in_group(self, rpi_ip: str) -> List[Dict]:
        """
        Get all devices in a specific R-Pi group
        
        Args:
            rpi_ip: R-Pi IP address
            
        Returns:
            List of device dicts in the group
        """
        if rpi_ip in self.groups:
            return self.groups[rpi_ip].devices
        return []
    
    def get_group_status(self, rpi_ip: str) -> Dict:
        """
        Get status of a tunnel group
        
        Returns:
            Dict with group information
        """
        if rpi_ip not in self.groups:
            return {'error': 'Group not found'}
        
        group = self.groups[rpi_ip]
        return {
            'rpi_ip': rpi_ip,
            'device_count': group.get_device_count(),
            'devices': [d['name'] for d in group.devices],
            'is_tunnel_established': group.is_tunnel_established,
            'tunnel_acquired_at': group.tunnel_acquired_at.isoformat() if group.tunnel_acquired_at else None
        }
    
    def print_execution_plan(self):
        """
        Print detailed execution plan (which devices execute together)
        """
        print("\n" + "="*80)
        print("EXECUTION PLAN - DEVICE GROUPING BY R-Pi CONFIGURATION")
        print("="*80)
        
        for idx, (rpi_ip, group) in enumerate(self.groups.items(), 1):
            print(f"\nPhase {idx}: R-Pi {rpi_ip}")
            print(f"└─ Tunnel Connection: Establish ONE tunnel for {group.get_device_count()} device(s)")
            for device in group.devices:
                print(f"   • {device['name']} ({device['ip']})")
            print(f"└─ Execution: All devices in this group execute IN PARALLEL")
        
        total_groups = len(self.groups)
        if total_groups > 1:
            print(f"\n✨ OPTIMIZATION: All {total_groups} groups execute SIMULTANEOUSLY (different R-Pis)")
            print(f"   → No sequential waiting needed")
            print(f"   → Maximum parallel execution achieved")
        else:
            print(f"\n✓ Single R-Pi group: All devices share one tunnel")
        
        print("="*80 + "\n")
    
    def reset(self):
        """Reset coordinator (for testing/cleanup)"""
        with self.lock:
            self.groups = {}
            self.group_tunnel_locks = {}
            print("[TUNNEL-GROUP-COORD] Coordinator reset")


# Global singleton instance
_tunnel_group_coordinator = TunnelGroupCoordinator()


def get_tunnel_group_coordinator() -> TunnelGroupCoordinator:
    """Get global tunnel group coordinator instance"""
    return _tunnel_group_coordinator

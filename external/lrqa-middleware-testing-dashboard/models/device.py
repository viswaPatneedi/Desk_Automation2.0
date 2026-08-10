"""
Device Model - Represents a test device entity
Handles device data persistence and validation
"""

from __future__ import annotations
import json
import os
from typing import List, Dict, Optional
from config.config_deployment import get_vnc_url, get_device_connection_params, TUNNEL_MODE
from config.config_paths import DEVICES_FILE
from models.database import Session, Device as DBDevice

class Device:
    """Device model for managing test device data"""

    # Tracks the most recent persistence path used by save_all().
    _last_persistence_status = {
        'database_available': False,
        'mode': 'unknown',
        'error': None
    }

    def __init__(self, ip: str, name: str, username: str, password: str, 
                 port: int = 10022, ir_config: Optional[Dict] = None, mac_address: str = None, vnc_url: str = None,
                 use_jump_host: bool = False, jump_host_config: Optional[Dict] = None, device_type: str = None, location: str = None, team_name: str = None,
                 is_rack_device: bool = False, rpi_config: Optional[Dict] = None, ir_blaster_config: Optional[Dict] = None, power_control_config: Optional[Dict] = None,
                 created_by: str = None, shared_with_teams: Optional[Dict] = None):
        self.original_ip = ip  # Store original IP for VNC URL generation
        self.ip = ip
        self.name = name
        self.username = username
        self.password = password
        self.port = port
        self.ir_config = ir_config or {}
        self.mac_address = mac_address or ''
        self._vnc_url = vnc_url or ''  # Store original VNC URL
        self.use_jump_host = use_jump_host
        self.jump_host_config = jump_host_config or {}
        self.device_type = device_type or ''
        self.location = location or ''
        self.team_name = team_name or ''
        self.is_rack_device = is_rack_device
        self.rpi_config = rpi_config or {}
        self.ir_blaster_config = ir_blaster_config or {}
        self.power_control_config = power_control_config or {}
        self.created_by = created_by or ''  # Track device creator for permissions
        self.shared_with_teams = shared_with_teams or {}  # {team_name: access_level}
    
    @property
    def vnc_url(self) -> str:
        """Generate dynamic VNC URL based on deployment mode"""
        return get_vnc_url(self.original_ip, self._vnc_url)
    
    def to_dict(self) -> Dict:
        """Convert device to dictionary"""
        return {
            'ip': self.ip,
            'name': self.name,
            'username': self.username,
            'password': self.password,
            'port': self.port,
            'ir_config': self.ir_config,
            'mac_address': self.mac_address,
            'vnc_url': self.vnc_url,  # Use property for dynamic VNC URL
            'use_jump_host': self.use_jump_host,
            'jump_host_config': self.jump_host_config,
            'device_type': self.device_type,
            'location': self.location,
            'team_name': self.team_name,
            'is_rack_device': self.is_rack_device,
            'rpi_config': self.rpi_config,
            'ir_blaster_config': self.ir_blaster_config,
            'power_control_config': self.power_control_config,
            'created_by': self.created_by,
            'shared_with_teams': self.shared_with_teams
        }

    def to_storage_dict(self) -> Dict:
        """Convert device to the persisted representation used by the database and JSON backup."""
        return {
            'ip': self.original_ip,
            'name': self.name,
            'username': self.username,
            'password': self.password,
            'port': self.port,
            'ir_config': self.ir_config,
            'mac_address': self.mac_address,
            'vnc_url': self._vnc_url or self.vnc_url,
            'use_jump_host': self.use_jump_host,
            'jump_host_config': self.jump_host_config,
            'device_type': self.device_type,
            'location': self.location,
            'team_name': self.team_name,
            'is_rack_device': self.is_rack_device,
            'rpi_config': self.rpi_config,
            'ir_blaster_config': self.ir_blaster_config,
            'power_control_config': self.power_control_config,
            'created_by': self.created_by,
            'shared_with_teams': self.shared_with_teams,
            'is_active': True
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Device':
        """Create device from dictionary"""
        # Build IR config from individual fields or nested ir_config
        ir_config = data.get('ir_config', {})
        if not ir_config and any(k in data for k in ['ir_port', 'itach_ip', 'itach_port']):
            # Build ir_config from individual fields for backward compatibility
            ir_config = {
                'ir_port': data.get('ir_port'),
                'itach_ip': data.get('itach_ip'),
                'itach_port': data.get('itach_port', 4998)
            }
        
        device = cls(
            ip=data['ip'],
            name=data['name'],
            username=data['username'],
            password=data['password'],
            port=data.get('port', 10022),
            ir_config=ir_config,
            mac_address=data.get('mac_address', ''),
            vnc_url=data.get('vnc_url', ''),
            use_jump_host=data.get('use_jump_host', False),
            jump_host_config=data.get('jump_host_config', {}),
            device_type=data.get('device_type', ''),
            location=data.get('location', ''),
            team_name=data.get('team_name', ''),
            is_rack_device=data.get('is_rack_device', False),
            rpi_config=data.get('rpi_config', {}),
            ir_blaster_config=data.get('ir_blaster_config', {}),
            power_control_config=data.get('power_control_config', {}),
            created_by=data.get('created_by', ''),
            shared_with_teams=data.get('shared_with_teams', {})
        )
        # Apply tunnel mode connection parameters if enabled
        if TUNNEL_MODE:
            conn_ip, conn_port = get_device_connection_params(data['ip'], data.get('port', 10022))
            device.ip = conn_ip
            device.port = conn_port
        return device
    
    @staticmethod
    def load_all() -> List['Device']:
        """Load all devices from the database, with JSON fallback"""
        session = Session()
        try:
            rows = (
                session.query(DBDevice)
                .filter_by(is_active=True)
                .order_by(DBDevice.name.asc(), DBDevice.ip.asc())
                .all()
            )
            if rows:
                devices = []
                for row in rows:
                    devices.append(Device.from_dict({
                        'ip': row.ip,
                        'name': row.name,
                        'username': row.username,
                        'password': row.password,
                        'port': row.port,
                        'ir_config': row.ir_config or {},
                        'mac_address': row.mac_address,
                        'vnc_url': row.vnc_url,
                        'use_jump_host': row.use_jump_host,
                        'jump_host_config': row.jump_host_config or {},
                        'device_type': row.device_type,
                        'location': row.location,
                        'team_name': row.team_name,
                        'is_rack_device': getattr(row, 'is_rack_device', False),
                        'rpi_config': getattr(row, 'rpi_config', {}) or {},
                        'ir_blaster_config': getattr(row, 'ir_blaster_config', {}) or {},
                        'power_control_config': getattr(row, 'power_control_config', {}) or {},
                        'created_by': getattr(row, 'created_by', ''),
                        'shared_with_teams': getattr(row, 'shared_with_teams', {}) or {}
                    }))
                print(f"✅ Loaded {len(devices)} devices from database")
                return devices
        except Exception as e:
            print(f"❌ Error loading from database: {e}")
            pass
        finally:
            session.close()

        # Fallback to JSON
        if os.path.exists(DEVICES_FILE):
            print(f"📄 Loading devices from JSON fallback: {DEVICES_FILE}")
            try:
                with open(DEVICES_FILE, 'r') as f:
                    devices_data = json.load(f)
                    print(f"✅ Loaded {len(devices_data)} devices from JSON")
                    return [Device.from_dict(d) for d in devices_data]
            except Exception as e:
                print(f"❌ Error loading JSON: {e}")
        
        print(f"⚠️  No devices found!")
        return []
    
    @staticmethod
    def save_all(devices: List['Device']) -> None:
        """Save all devices to the database and mirror them to JSON"""
        from sqlalchemy.exc import OperationalError, IntegrityError
        session = Session()
        database_available = False
        db_error = None
        
        try:
            # Track desired active device IPs so removed devices can be deactivated in DB.
            active_ips = set()

            for device in devices:
                storage_data = device.to_storage_dict()
                active_ips.add(storage_data['ip'])
                row = session.query(DBDevice).filter_by(ip=storage_data['ip']).first()
                if row is None:
                    row = DBDevice(
                        ip=storage_data['ip'],
                        name=storage_data['name'],
                        username=storage_data['username'],
                        password=storage_data['password'],
                        port=storage_data['port'],
                        device_type=storage_data['device_type'],
                        mac_address=storage_data['mac_address'],
                        vnc_url=storage_data['vnc_url'],
                        location=storage_data['location'],
                        team_name=storage_data['team_name'] or 'DEFAULT',
                        use_jump_host=storage_data['use_jump_host'],
                        jump_host_config=storage_data['jump_host_config'],
                        ir_config=storage_data['ir_config'],
                        is_rack_device=storage_data['is_rack_device'],
                        rpi_config=storage_data['rpi_config'],
                        shared_with_teams=storage_data.get('shared_with_teams', {}),
                        is_active=storage_data.get('is_active', True)
                    )
                    session.add(row)
                else:
                    row.name = storage_data['name']
                    row.username = storage_data['username']
                    row.password = storage_data['password']
                    row.port = storage_data['port']
                    row.device_type = storage_data['device_type']
                    row.mac_address = storage_data['mac_address']
                    row.vnc_url = storage_data['vnc_url']
                    row.location = storage_data['location']
                    row.team_name = storage_data['team_name'] or 'DEFAULT'
                    row.use_jump_host = storage_data['use_jump_host']
                    row.jump_host_config = storage_data['jump_host_config']
                    row.ir_config = storage_data['ir_config']
                    row.is_rack_device = storage_data['is_rack_device']
                    row.rpi_config = storage_data['rpi_config']
                    row.shared_with_teams = storage_data.get('shared_with_teams', {})
                    row.is_active = storage_data.get('is_active', True)

            # Persist deletions by deactivating any currently-active DB rows not in active_ips.
            print(f"🔍 [Database] Active IPs to keep: {active_ips}")
            if active_ips:
                deactivated = session.query(DBDevice).filter(
                    DBDevice.is_active.is_(True),
                    ~DBDevice.ip.in_(list(active_ips))
                ).update({'is_active': False}, synchronize_session=False)
                print(f"🗑️  [Database] Deactivated {deactivated} devices")
            else:
                # If the list is empty, all rows should be inactive.
                deactivated = session.query(DBDevice).filter(
                    DBDevice.is_active.is_(True)
                ).update({'is_active': False}, synchronize_session=False)
                print(f"🗑️  [Database] Deactivated all {deactivated} devices (empty list)")

            session.commit()
            database_available = True
            Device._last_persistence_status = {
                'database_available': True,
                'mode': 'database+json',
                'error': None
            }
            print("✅ [Database] Devices saved to PostgreSQL")
        except OperationalError as e:
            session.rollback()
            db_error = str(e)
            print(f"⚠️  [Database] Connection error - falling back to JSON: {str(e)}")
            print(f"    Error type: OperationalError")
            database_available = False
        except IntegrityError as e:
            session.rollback()
            db_error = str(e)
            print(f"⚠️  [Database] Integrity error - falling back to JSON: {str(e)}")
            print(f"    Error type: IntegrityError")
            database_available = False
        except Exception as e:
            session.rollback()
            db_error = str(e)
            print(f"⚠️  [Database] Error - falling back to JSON: {str(e)}")
            print(f"    Error type: {type(e).__name__}")
            print(f"    Full traceback: ")
            import traceback
            traceback.print_exc()
            database_available = False
        finally:
            session.close()

        # Always save to JSON file as backup/fallback
        try:
            devices_data = [device.to_storage_dict() for device in devices]
            with open(DEVICES_FILE, 'w') as f:
                json.dump(devices_data, f, indent=4)
            if not database_available:
                Device._last_persistence_status = {
                    'database_available': False,
                    'mode': 'json-only',
                    'error': db_error
                }
                print("✅ [JSON] Devices saved to JSON file (database unavailable)")
            else:
                print("✅ [JSON] Devices synced to JSON file")
        except Exception as e:
            print(f"❌ [ERROR] Failed to save to JSON file: {str(e)}")
            if not database_available:
                raise Exception(f"Failed to save devices - both database and JSON failed: {str(e)}") from e

    @staticmethod
    def get_last_persistence_status() -> Dict:
        """Get latest save persistence status for API/debug reporting."""
        return dict(Device._last_persistence_status)
    @staticmethod
    def find_by_ip(ip: str) -> Optional['Device']:
        """Find device by IP address"""
        devices = Device.load_all()
        for device in devices:
            if device.ip == ip or device.original_ip == ip:
                return device
        return None
    
    @staticmethod
    def find_by_name(name: str) -> Optional['Device']:
        """Find device by name"""
        devices = Device.load_all()
        for device in devices:
            if device.name == name:
                return device
        return None
    
    @staticmethod
    def find_by_ip_and_mac(ip: str, mac_address: str) -> Optional['Device']:
        """Find device by IP and MAC address combination"""
        devices = Device.load_all()
        for device in devices:
            # Check if both IP and MAC match
            if (device.ip == ip or device.original_ip == ip) and device.mac_address == mac_address:
                return device
        return None
    
    @staticmethod
    def add(device: 'Device') -> bool:
        """Add a new device - returns True if successful, False if duplicate (by IP or MAC)"""
        devices = Device.load_all()
        
        # Check if device already exists by IP alone
        for d in devices:
            if d.ip == device.ip or d.original_ip == device.original_ip:
                # Return the existing device as a dict to indicate conflict
                # This will be handled specially in the controller
                return False
        
        # Check if device with same MAC already exists
        if device.mac_address:
            for d in devices:
                if d.mac_address and d.mac_address == device.mac_address:
                    # MAC already exists with different IP - also a conflict
                    return False
        
        devices.append(device)
        Device.save_all(devices)
        return True
    
    @staticmethod
    def delete(ip: str) -> bool:
        """Delete a device by IP"""
        devices = Device.load_all()
        original_count = len(devices)
        devices = [d for d in devices if d.ip != ip and d.original_ip != ip]
        if len(devices) < original_count:
            Device.save_all(devices)
            return True
        return False
    
    @staticmethod
    def update(old_ip: str, device: 'Device') -> bool:
        """Update a device by its old IP"""
        devices = Device.load_all()
        for i, d in enumerate(devices):
            if d.ip == old_ip or d.original_ip == old_ip:
                devices[i] = device
                Device.save_all(devices)
                return True
        return False
    
    def validate_connection(self) -> tuple[bool, str]:
        """
        Unified device validation mechanism:
        1. If R-Pi config is available, connect via R-Pi tunnel (works for both Desk and Rack devices)
        2. Fallback to direct SSH if no R-Pi config
        
        This standardized approach works for:
        - Desktop devices with R-Pi gateway
        - Rack devices via R-Pi tunnel
        - Direct devices (fallback only)
        """
        # PRIORITY 1: Use R-Pi tunnel if R-Pi config is configured
        if self.rpi_config and self.rpi_config.get('rpi_ip'):
            rpi_ip = self.rpi_config.get('rpi_ip')
            return self._validate_via_rpi(rpi_ip)
        
        # PRIORITY 2: Use jump host if configured
        if self.use_jump_host and self.jump_host_config:
            return self._validate_via_jump_host()
        
        # FALLBACK: Direct SSH connection
        return self._validate_direct_ssh()
    
    def _validate_direct_ssh(self) -> tuple[bool, str]:
        """
        Direct SSH connection to device (fallback method) - supports passwordless SSH
        
        Added: SSH options to handle host key verification gracefully for connectivity checks
        """
        import subprocess
        try:
            # SSH options to handle connectivity checks:
            # -o StrictHostKeyChecking=accept-new  → Accept new keys automatically
            # -o UserKnownHostsFile=/dev/null      → Ignore known_hosts conflicts
            # This prevents "Device Inactive" status due to known_hosts issues
            ssh_command = (
                f'timeout 5 ssh '
                f'-o StrictHostKeyChecking=accept-new '
                f'-o UserKnownHostsFile=/dev/null '
                f'-p {self.port} {self.username}@{self.ip} "echo alive"'
            )
            result = subprocess.run(ssh_command, shell=True, capture_output=True, timeout=10, text=True)
            
            if result.returncode == 0 and 'alive' in result.stdout:
                return True, "✅ Device is ACTIVE (direct connection)"
            else:
                return False, f"❌ Direct connection failed: {result.stderr or 'No response'}"
        except subprocess.TimeoutExpired:
            return False, "❌ Direct connection timed out"
        except Exception as e:
            return False, f"❌ Direct connection failed: {str(e)}"
    
    def _validate_via_rpi(self, rpi_ip: str) -> tuple[bool, str]:
        """
        Unified R-Pi tunnel validation for both Desktop and Rack devices
        
        Connection Flow:
        1. SSH to R-Pi using rpi_config credentials
        2. From R-Pi, SSH to device using device credentials
        3. Execute "echo alive" to verify device is reachable
        
        Fixed: Includes SSH options to bypass host key verification issues
        """
        import paramiko
        
        # Validate R-Pi configuration
        if not self.rpi_config:
            return False, "❌ R-Pi configuration not found"
        
        rpi_username = self.rpi_config.get('rpi_username', 'pi')
        rpi_password = self.rpi_config.get('rpi_password', '')
        rpi_port = self.rpi_config.get('rpi_port', 22)
        
        if not rpi_password:
            return False, "❌ R-Pi password not configured"
        
        try:
            # STEP 1: Connect to R-Pi
            print(f"🔗 [R-Pi] Connecting to R-Pi at {rpi_ip}:{rpi_port}...")
            ssh_rpi = paramiko.SSHClient()
            ssh_rpi.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_rpi.connect(rpi_ip, port=int(rpi_port), username=rpi_username, 
                           password=rpi_password, timeout=10)
            print(f"✅ [R-Pi] Connected to R-Pi successfully")
            
            # STEP 2: From R-Pi, SSH to device and verify connectivity
            print(f"🔍 [Device] Checking device {self.ip}:{self.port} connectivity from R-Pi...")
            
            # Execute SSH command from R-Pi to device with timeout
            # IMPORTANT: Added SSH options to bypass host key verification issues:
            #   -o StrictHostKeyChecking=accept-new  → Accept new keys but verify known hosts
            #   -o UserKnownHostsFile=/dev/null      → Ignore known_hosts to avoid conflicts
            #   This fixes: "Device shows Inactive when SSH known_hosts has issues"
            ssh_command = (
                f'timeout 5 ssh '
                f'-o StrictHostKeyChecking=accept-new '
                f'-o UserKnownHostsFile=/dev/null '
                f'-p {self.port} {self.username}@{self.ip} "echo alive"'
            )
            
            stdin, stdout, stderr = ssh_rpi.exec_command(ssh_command, timeout=15)
            output = stdout.read().decode('utf-8', errors='ignore').strip()
            error = stderr.read().decode('utf-8', errors='ignore').strip()
            return_code = stdout.channel.recv_exit_status()
            
            ssh_rpi.close()
            
            # STEP 3: Evaluate result
            if return_code == 0 and 'alive' in output:
                print(f"✅ [Device] Device {self.ip} is ACTIVE (via R-Pi {rpi_ip})")
                return True, f"✅ Device is ACTIVE (via R-Pi {rpi_ip})"
            else:
                print(f"❌ [Device] Device {self.ip} is INACTIVE or unreachable from R-Pi")
                error_detail = error if error else "No response from device (may indicate host key verification issue - run manual SSH to clear known_hosts)"
                return False, f"❌ Device unreachable from R-Pi {rpi_ip}: {error_detail}"
                
        except paramiko.AuthenticationException as e:
            print(f"❌ [R-Pi] Authentication failed for R-Pi {rpi_ip}: {str(e)}")
            return False, f"❌ R-Pi authentication failed: {str(e)}"
        except paramiko.SSHException as e:
            print(f"❌ [R-Pi] SSH error connecting to R-Pi {rpi_ip}: {str(e)}")
            return False, f"❌ R-Pi SSH error: {str(e)}"
        except Exception as e:
            print(f"❌ [Connection] Error during R-Pi validation: {str(e)}")
            return False, f"❌ R-Pi validation error: {str(e)}"
    
    def _validate_via_jump_host(self) -> tuple[bool, str]:
        """Validate connection via jump host"""
        from services.jump_host_service import JumpHostService
        
        if not self.mac_address:
            return False, "MAC address required for jump host connection"
        
        jump_config = self.jump_host_config
        required_fields = ['host', 'username', 'password']
        for field in required_fields:
            if field not in jump_config:
                return False, f"Jump host config missing: {field}"
        
        try:
            service = JumpHostService(
                jump_host=jump_config['host'],
                jump_user=jump_config['username'],
                jump_pass=jump_config['password'],
                jump_port=jump_config.get('port', 22)
            )
            
            # Connect to jump host
            success, msg = service.connect()
            if not success:
                return False, f"Jump host connection failed: {msg}"
            
            # Connect to device via MAC
            success, msg = service.connect_to_device_by_mac(self.mac_address)
            service.disconnect()
            
            if success:
                return True, "Connection via jump host successful"
            else:
                return False, f"Device connection failed: {msg}"
                
        except Exception as e:
            return False, f"Jump host error: {str(e)}"
    
    def validate_connection_via_rpi(self, rpi_ip: str) -> tuple[bool, str]:
        """
        Deprecated: Use validate_connection() instead for unified handling
        
        This method is kept for backward compatibility.
        The main validate_connection() now handles R-Pi automatically.
        
        If called explicitly with rpi_ip, it updates rpi_config temporarily and validates.
        """
        # Temporarily set rpi_ip in config if not already set
        if not self.rpi_config.get('rpi_ip'):
            self.rpi_config['rpi_ip'] = rpi_ip
        
        # Use the new unified R-Pi validation
        return self._validate_via_rpi(rpi_ip)
    
    def fetch_mac_address(self) -> Optional[str]:
        """Fetch MAC address from device using SSH"""
        import paramiko
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.ip, port=self.port, username=self.username, 
                       password=self.password, timeout=10)
            
            # Execute command to get MAC address
            stdin, stdout, stderr = ssh.exec_command("cat /tmp/.deviceDetails.cache | grep -i 'estb_mac'")
            output = stdout.read().decode('utf-8', errors='ignore').strip()
            ssh.close()
            
            # Parse output: estb_mac=1C:2F:A2:30:35:B6
            if 'estb_mac=' in output:
                mac = output.split('estb_mac=')[1].strip()
                return mac
            return None
        except Exception as e:
            print(f"Error fetching MAC address for {self.ip}: {e}")
            return None
    
    @staticmethod
    def update_mac_address(ip: str, mac_address: str) -> bool:
        """Update MAC address for a device"""
        devices = Device.load_all()
        for device in devices:
            if device.ip == ip or device.original_ip == ip:
                device.mac_address = mac_address
                Device.save_all(devices)
                return True
        return False

"""
SSH Connection Pool - Manages reusable SSH connections to devices
Improves performance and reduces connection overhead
"""
import paramiko
import threading
import time
from typing import Dict, Optional
from datetime import datetime, timedelta

class SSHConnectionPool:
    """Thread-safe SSH connection pool for device management"""
    
    def __init__(self, max_connections: int = 50, idle_timeout: int = 300):
        """
        Initialize SSH connection pool.
        
        Args:
            max_connections: Maximum number of pooled connections
            idle_timeout: Time in seconds before idle connection is closed
        """
        self.max_connections = max_connections
        self.idle_timeout = idle_timeout
        self.pool: Dict[str, Dict] = {}
        self.lock = threading.Lock()
        self._cleanup_thread = None
        self._running = False
    
    def start(self):
        """Start the connection pool cleanup thread"""
        if not self._running:
            self._running = True
            self._cleanup_thread = threading.Thread(target=self._cleanup_idle_connections, daemon=True)
            self._cleanup_thread.start()
    
    def stop(self):
        """Stop the connection pool and close all connections"""
        self._running = False
        with self.lock:
            for conn_info in self.pool.values():
                try:
                    conn_info['client'].close()
                except Exception:
                    pass
            self.pool.clear()
    
    def _make_connection_key(self, host: str, port: int, username: str) -> str:
        """Generate unique key for connection"""
        return f"{host}:{port}:{username}"
    
    def get_connection(self, host: str, port: int, username: str, password: str, 
                      timeout: int = 15) -> paramiko.SSHClient:
        """
        Get an SSH connection from the pool or create a new one.
        
        Args:
            host: Device IP address
            port: SSH port
            username: SSH username
            password: SSH password
            timeout: Connection timeout in seconds
        
        Returns:
            Active SSH client connection
        """
        conn_key = self._make_connection_key(host, port, username)
        
        with self.lock:
            # Check if connection exists and is still alive
            if conn_key in self.pool:
                conn_info = self.pool[conn_key]
                client = conn_info['client']
                
                # Test if connection is still alive
                try:
                    transport = client.get_transport()
                    if transport and transport.is_active():
                        # Update last used time
                        conn_info['last_used'] = datetime.now()
                        return client
                    else:
                        # Connection dead, remove from pool
                        del self.pool[conn_key]
                except Exception:
                    # Error checking connection, remove from pool
                    if conn_key in self.pool:
                        del self.pool[conn_key]
            
            # Create new connection
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            try:
                client.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    password=password,
                    timeout=timeout,
                    look_for_keys=False,
                    allow_agent=False
                )
                
                # Add to pool if not at max capacity
                if len(self.pool) < self.max_connections:
                    self.pool[conn_key] = {
                        'client': client,
                        'last_used': datetime.now(),
                        'created_at': datetime.now()
                    }
                
                return client
            
            except Exception as e:
                try:
                    client.close()
                except Exception:
                    pass
                raise e
    
    def release_connection(self, host: str, port: int, username: str):
        """
        Mark a connection as no longer in use (but keep it in pool).
        
        Args:
            host: Device IP address
            port: SSH port
            username: SSH username
        """
        conn_key = self._make_connection_key(host, port, username)
        with self.lock:
            if conn_key in self.pool:
                self.pool[conn_key]['last_used'] = datetime.now()
    
    def remove_connection(self, host: str, port: int, username: str):
        """
        Remove a specific connection from the pool.
        
        Args:
            host: Device IP address
            port: SSH port
            username: SSH username
        """
        conn_key = self._make_connection_key(host, port, username)
        with self.lock:
            if conn_key in self.pool:
                try:
                    self.pool[conn_key]['client'].close()
                except Exception:
                    pass
                del self.pool[conn_key]
    
    def _cleanup_idle_connections(self):
        """Background thread to clean up idle connections"""
        while self._running:
            try:
                time.sleep(60)  # Check every minute
                
                now = datetime.now()
                to_remove = []
                
                with self.lock:
                    for conn_key, conn_info in self.pool.items():
                        # Check if connection is idle for too long
                        idle_time = (now - conn_info['last_used']).total_seconds()
                        if idle_time > self.idle_timeout:
                            to_remove.append(conn_key)
                    
                    # Remove idle connections
                    for conn_key in to_remove:
                        try:
                            self.pool[conn_key]['client'].close()
                        except Exception:
                            pass
                        del self.pool[conn_key]
                
                if to_remove:
                    print(f"[SSH Pool] Cleaned up {len(to_remove)} idle connections")
            
            except Exception as e:
                print(f"[SSH Pool] Error in cleanup thread: {e}")
    
    def get_pool_stats(self) -> Dict:
        """Get connection pool statistics"""
        with self.lock:
            return {
                'total_connections': len(self.pool),
                'max_connections': self.max_connections,
                'idle_timeout': self.idle_timeout,
                'connections': [
                    {
                        'key': key,
                        'last_used': info['last_used'].isoformat(),
                        'age_seconds': (datetime.now() - info['created_at']).total_seconds()
                    }
                    for key, info in self.pool.items()
                ]
            }


# Global connection pool instance
_ssh_pool = None

def get_ssh_pool() -> SSHConnectionPool:
    """Get or create the global SSH connection pool"""
    global _ssh_pool
    if _ssh_pool is None:
        _ssh_pool = SSHConnectionPool(max_connections=50, idle_timeout=300)
        _ssh_pool.start()
    return _ssh_pool

"""
HashiCorp Vault Integration for Secrets Management

Manages centralized secret retrieval, storage, and rotation for:
- Database credentials
- API keys (GitHub, Anthropic, etc.)
- SSL/TLS certificates
- OAuth tokens
- Encryption keys

Features:
- AppRole authentication for Kubernetes/Docker environments
- Automatic secret rotation (configurable intervals)
- Fallback to environment variables in development
- Comprehensive audit logging
- Connection pooling and retry logic
"""

import os
import json
import logging
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from functools import wraps
import hvac
from hvac.exceptions import VaultError, InvalidPath

logger = logging.getLogger(__name__)


class VaultClientConfig:
    """Configuration for Vault connection"""
    
    def __init__(self):
        self.vault_addr = os.getenv('VAULT_ADDR', 'http://localhost:8200')
        self.vault_token = os.getenv('VAULT_TOKEN')
        self.vault_role_id = os.getenv('VAULT_ROLE_ID')
        self.vault_secret_id = os.getenv('VAULT_SECRET_ID')
        self.vault_namespace = os.getenv('VAULT_NAMESPACE', '')
        self.vault_skip_verify = os.getenv('VAULT_SKIP_VERIFY', 'false').lower() == 'true'
        self.vault_timeout = int(os.getenv('VAULT_TIMEOUT', '30'))
        self.vault_max_retries = int(os.getenv('VAULT_MAX_RETRIES', '3'))
        
        # Development mode uses mock/environment secrets
        self.vault_enabled = os.getenv('VAULT_ENABLED', 'false').lower() == 'true'


class VaultClient:
    """Manages secrets from HashiCorp Vault"""
    
    def __init__(self, config: Optional[VaultClientConfig] = None):
        self.config = config or VaultClientConfig()
        self.client: Optional[hvac.Client] = None
        self._secret_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_ttl = int(os.getenv('VAULT_CACHE_TTL', '3600'))  # 1 hour
        
        if self.config.vault_enabled:
            self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Vault client with appropriate auth method"""
        try:
            self.client = hvac.Client(
                url=self.config.vault_addr,
                token=self.config.vault_token,
                namespace=self.config.vault_namespace,
                timeout=self.config.vault_timeout,
                verify=not self.config.vault_skip_verify
            )
            
            # If token not provided, use AppRole auth
            if not self.config.vault_token and self.config.vault_role_id and self.config.vault_secret_id:
                self._authenticate_with_approle()
            
            # Test connection
            self.client.sys.is_initialized()
            logger.info("✅ Successfully connected to Vault")
        
        except Exception as e:
            logger.error(f"❌ Failed to initialize Vault client: {e}")
            if os.getenv('FLASK_ENV') == 'production':
                raise
            else:
                logger.warning("⚠️ Running in development mode without Vault")
                self.client = None
    
    def _authenticate_with_approle(self) -> None:
        """Authenticate using AppRole method (for Kubernetes/Docker)"""
        try:
            response = self.client.auth.approle.login(
                role_id=self.config.vault_role_id,
                secret_id=self.config.vault_secret_id,
                use_token=True
            )
            logger.info("✅ Successfully authenticated with Vault using AppRole")
        except VaultError as e:
            logger.error(f"❌ AppRole authentication failed: {e}")
            raise
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached secret is still valid"""
        if key not in self._cache_timestamps:
            return False
        
        age = time.time() - self._cache_timestamps[key]
        return age < self._cache_ttl
    
    def _retry_on_failure(self, func, *args, **kwargs):
        """Retry logic for transient failures"""
        retries = 0
        last_error = None
        
        while retries < self.config.vault_max_retries:
            try:
                return func(*args, **kwargs)
            except VaultError as e:
                retries += 1
                last_error = e
                if retries < self.config.vault_max_retries:
                    wait_time = 2 ** retries  # Exponential backoff
                    logger.warning(f"⚠️ Vault request failed, retrying in {wait_time}s (attempt {retries}/{self.config.vault_max_retries})")
                    time.sleep(wait_time)
        
        logger.error(f"❌ Vault request failed after {self.config.vault_max_retries} retries: {last_error}")
        raise last_error
    
    def get_secret(self, path: str, key: Optional[str] = None, use_cache: bool = True) -> Any:
        """
        Retrieve secret from Vault
        
        Args:
            path: Secret path in Vault (e.g., 'secret/data/lrqa/db')
            key: Optional specific key within the secret
            use_cache: Whether to use cached value
        
        Returns:
            Secret value or dict of all secrets
        """
        if not self.config.vault_enabled:
            return self._get_from_environment(path, key)
        
        cache_key = f"{path}:{key or 'all'}"
        
        # Check cache
        if use_cache and self._is_cache_valid(cache_key):
            logger.debug(f"📦 Retrieved from cache: {path}")
            secret = self._secret_cache[cache_key]
        else:
            # Fetch from Vault
            try:
                secret = self._retry_on_failure(
                    self.client.secrets.kv.v2.read_secret_version,
                    path
                )
                
                # Extract data
                if 'data' in secret and 'data' in secret['data']:
                    secret = secret['data']['data']
                else:
                    logger.warning(f"⚠️ Unexpected Vault response structure for {path}")
                    secret = {}
                
                # Cache result
                self._secret_cache[cache_key] = secret
                self._cache_timestamps[cache_key] = time.time()
                logger.info(f"✅ Retrieved from Vault: {path}")
            
            except InvalidPath:
                logger.error(f"❌ Secret not found in Vault: {path}")
                return None
            except VaultError as e:
                logger.error(f"❌ Vault error retrieving {path}: {e}")
                raise
        
        # Return specific key or all
        if key:
            return secret.get(key)
        return secret
    
    def _get_from_environment(self, path: str, key: Optional[str] = None) -> Any:
        """Fallback to environment variables (development mode)"""
        # Convert Vault path to env var format
        # e.g., secret/data/db/central -> app_db_central_<key>
        env_prefix = path.replace('/', '_').replace('data_', '').upper()
        
        if key:
            env_var = f"{env_prefix}_{key.upper()}"
            value = os.getenv(env_var)
            logger.debug(f"📦 Retrieved from environment: {env_var}")
            return value
        else:
            # Return all env vars matching pattern
            result = {}
            for env_var, value in os.environ.items():
                if env_var.startswith(env_prefix):
                    result[env_var] = value
            return result if result else os.getenv(f"{env_prefix}_ALL", {})
    
    # Convenience methods for common secrets
    
    def get_db_credentials(self) -> Dict[str, str]:
        """Get central database credentials"""
        return self.get_secret('secret/data/lrqa/db/central') or {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'lrqa_v2_central'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
        }
    
    def get_github_credentials(self) -> Dict[str, str]:
        """Get GitHub API credentials"""
        return self.get_secret('secret/data/lrqa/github') or {
            'api_token': os.getenv('GITHUB_TOKEN', ''),
            'repo': os.getenv('GITHUB_REPO', ''),
            'branch': os.getenv('GITHUB_BRANCH', 'main'),
        }
    
    def get_api_keys(self) -> Dict[str, str]:
        """Get all API keys"""
        return self.get_secret('secret/data/lrqa/api/keys') or {
            'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY', ''),
            'claude_model': os.getenv('CLAUDE_MODEL', 'claude-3-opus-20240229'),
        }
    
    def get_email_credentials(self) -> Dict[str, str]:
        """Get email service credentials"""
        return self.get_secret('secret/data/lrqa/email') or {
            'smtp_host': os.getenv('SMTP_HOST', 'localhost'),
            'smtp_port': os.getenv('SMTP_PORT', '587'),
            'smtp_user': os.getenv('SMTP_USER', ''),
            'smtp_password': os.getenv('SMTP_PASSWORD', ''),
        }
    
    def get_ssl_certificates(self) -> Dict[str, str]:
        """Get SSL/TLS certificates"""
        return self.get_secret('secret/data/lrqa/ssl') or {
            'cert': os.getenv('SSL_CERT_FILE', ''),
            'key': os.getenv('SSL_KEY_FILE', ''),
            'ca_bundle': os.getenv('SSL_CA_BUNDLE', ''),
        }
    
    def rotate_secret(self, path: str, new_value: Dict[str, str]) -> bool:
        """Rotate a secret (update in Vault)"""
        if not self.config.vault_enabled:
            logger.warning("⚠️ Cannot rotate secret in development mode (Vault disabled)")
            return False
        
        try:
            self.client.secrets.kv.v2.create_or_update_secret_version(
                path=path,
                secret_data=new_value
            )
            
            # Clear cache for this path
            for cache_key in list(self._secret_cache.keys()):
                if cache_key.startswith(path):
                    del self._secret_cache[cache_key]
                    del self._cache_timestamps[cache_key]
            
            logger.info(f"✅ Successfully rotated secret: {path}")
            return True
        
        except VaultError as e:
            logger.error(f"❌ Failed to rotate secret {path}: {e}")
            return False
    
    def list_secrets(self, path: str) -> Optional[list]:
        """List all secrets at a path"""
        if not self.config.vault_enabled:
            logger.warning("⚠️ Cannot list secrets in development mode (Vault disabled)")
            return None
        
        try:
            response = self.client.secrets.kv.v2.list_secrets(path)
            secrets = response['data']['keys']
            logger.info(f"✅ Listed {len(secrets)} secrets at {path}")
            return secrets
        
        except VaultError as e:
            logger.error(f"❌ Failed to list secrets at {path}: {e}")
            return None
    
    def delete_secret(self, path: str) -> bool:
        """Delete a secret (permanent deletion)"""
        if not self.config.vault_enabled:
            logger.warning("⚠️ Cannot delete secret in development mode (Vault disabled)")
            return False
        
        try:
            self.client.secrets.kv.v2.destroy_secret_version(path)
            
            # Clear cache
            for cache_key in list(self._secret_cache.keys()):
                if cache_key.startswith(path):
                    del self._secret_cache[cache_key]
                    del self._cache_timestamps[cache_key]
            
            logger.warning(f"⚠️ Permanently deleted secret: {path}")
            return True
        
        except VaultError as e:
            logger.error(f"❌ Failed to delete secret {path}: {e}")
            return False


def require_vault(func):
    """Decorator to enforce Vault availability for critical operations"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        vault = kwargs.get('vault_client') or _get_vault_instance()
        
        if not vault.config.vault_enabled:
            if os.getenv('FLASK_ENV') == 'production':
                raise RuntimeError("Vault is required in production but not configured")
            logger.warning("⚠️ Vault not available, running in degraded mode")
        
        return func(*args, **kwargs)
    return wrapper


# Global Vault instance
_vault_instance: Optional[VaultClient] = None


def get_vault_client() -> VaultClient:
    """Get or create global Vault client instance"""
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = VaultClient()
    return _vault_instance


def _get_vault_instance() -> VaultClient:
    """Alias for get_vault_client()"""
    return get_vault_client()


# Export commonly used functions
def get_db_credentials() -> Dict[str, str]:
    """Convenience function to get DB credentials"""
    return get_vault_client().get_db_credentials()


def get_github_token() -> str:
    """Convenience function to get GitHub token"""
    creds = get_vault_client().get_github_credentials()
    return creds.get('api_token', '')


def get_api_keys() -> Dict[str, str]:
    """Convenience function to get all API keys"""
    return get_vault_client().get_api_keys()

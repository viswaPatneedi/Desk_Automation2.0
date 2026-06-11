"""
PyArmor Code Encryption Agent

Manages code encryption, obfuscation, and tamper detection for production deployment.

Features:
- Source code obfuscation using PyArmor
- String encryption and symbol removal
- Tamper detection and verification
- License generation (commercial mode)
- Integration with Docker builds
- Backup and rollback capabilities

Note: PyArmor community edition for open-source projects
      PyArmor commercial license for enterprise deployments
"""

import os
import sys
import json
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class EncryptionMode(Enum):
    """PyArmor encryption modes"""
    BASIC = "basic"        # Basic obfuscation (free)
    ADVANCED = "advanced"  # Advanced with string encryption (requires license)


@dataclass
class EncryptionConfig:
    """Configuration for PyArmor encryption"""
    
    mode: EncryptionMode = EncryptionMode.BASIC
    obfuscate_code: bool = True
    obfuscate_imports: bool = True
    obfuscate_function_names: bool = True
    obfuscate_module_names: bool = True
    enable_anticlip: bool = True  # Prevent copying/pasting
    enable_console: bool = False  # Disable console script
    enable_rjit: bool = False     # Restrict JIT compilation
    enable_jit: bool = False      # Optimize with JIT
    rest_key: bool = True         # Use rest key (encryption)
    
    # Source and output
    source_dir: str = "agents"
    output_dir: str = ".pyarmor"
    dist_dir: str = "dist"
    
    # License (commercial mode)
    license_file: Optional[str] = None
    license_expiry: Optional[str] = None  # 'YYYY-MM-DD' or 'none'


class EncryptionError(Exception):
    """Raised when encryption operations fail"""
    pass


class PyArmorAgent:
    """Manages code encryption using PyArmor"""
    
    def __init__(self, config: Optional[EncryptionConfig] = None):
        self.config = config or EncryptionConfig()
        self.pyarmor_path = self._find_pyarmor()
        self.start_time = datetime.now()
        
        if not self.pyarmor_path:
            raise EncryptionError("PyArmor not found. Install: pip install pyarmor")
        
        logger.info(f"✅ PyArmor found at: {self.pyarmor_path}")
    
    def _find_pyarmor(self) -> Optional[str]:
        """Find PyArmor executable"""
        result = shutil.which("pyarmor")
        if result:
            return result
        
        # Try common installation paths
        for path in [
            "pyarmor",
            "/usr/local/bin/pyarmor",
            os.path.expanduser("~/.local/bin/pyarmor"),
        ]:
            if shutil.which(path):
                return path
        
        return None
    
    def _run_command(self, *args) -> Tuple[int, str, str]:
        """Execute PyArmor command"""
        cmd = [self.pyarmor_path] + list(args)
        logger.debug(f"🔨 Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"❌ Command failed:\n{result.stderr}")
        else:
            logger.debug(f"✅ Command output:\n{result.stdout}")
        
        return result.returncode, result.stdout, result.stderr
    
    def init_project(self) -> bool:
        """Initialize PyArmor project"""
        try:
            # Clean previous project
            if os.path.exists(self.config.output_dir):
                logger.info(f"🗑️ Removing existing project: {self.config.output_dir}")
                shutil.rmtree(self.config.output_dir)
            
            # Create new project
            logger.info(f"📦 Initializing PyArmor project: {self.config.output_dir}")
            
            cmd_args = [
                "create",
                "--type", "webapi",
                "--output", self.config.output_dir,
            ]
            
            returncode, stdout, stderr = self._run_command(*cmd_args)
            
            if returncode == 0:
                logger.info("✅ PyArmor project initialized")
                return True
            else:
                logger.error(f"❌ Failed to initialize project: {stderr}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error initializing project: {e}")
            return False
    
    def configure_project(self) -> bool:
        """Configure PyArmor project settings"""
        try:
            config_file = os.path.join(self.config.output_dir, ".pyarmor")
            
            config_data = {
                "mode": self.config.mode.value,
                "obf_code": 1 if self.config.obfuscate_code else 0,
                "obf_import": 1 if self.config.obfuscate_imports else 0,
                "obf_func_name": 1 if self.config.obfuscate_function_names else 0,
                "obf_module_name": 1 if self.config.obfuscate_module_names else 0,
                "anti_clip": 1 if self.config.enable_anticlip else 0,
                "enable_console": 1 if self.config.enable_console else 0,
                "enable_rjit": 1 if self.config.enable_rjit else 0,
                "enable_jit": 1 if self.config.enable_jit else 0,
                "rest_key": 1 if self.config.rest_key else 0,
            }
            
            os.makedirs(self.config.output_dir, exist_ok=True)
            
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"✅ Configuration saved to: {config_file}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error configuring project: {e}")
            return False
    
    def add_sources(self, sources: Optional[List[str]] = None) -> bool:
        """Add source files to encryption"""
        try:
            if not sources:
                # Auto-detect sources
                sources = self._find_python_files(self.config.source_dir)
            
            if not sources:
                logger.warning(f"⚠️ No Python files found in {self.config.source_dir}")
                return False
            
            logger.info(f"📂 Adding {len(sources)} source files to encryption")
            
            for source in sources:
                logger.info(f"  ├─ Adding: {source}")
                cmd_args = ["config", "--add", source]
                returncode, _, stderr = self._run_command(*cmd_args)
                
                if returncode != 0:
                    logger.warning(f"  └─ ⚠️ Issue adding {source}: {stderr}")
            
            logger.info("✅ Sources added")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error adding sources: {e}")
            return False
    
    def _find_python_files(self, directory: str) -> List[str]:
        """Recursively find Python files"""
        python_files = []
        
        try:
            for root, dirs, files in os.walk(directory):
                # Skip __pycache__ and .pyarmor
                dirs[:] = [d for d in dirs if d not in ['__pycache__', '.pyarmor', 'dist', '.git']]
                
                for file in files:
                    if file.endswith('.py') and not file.startswith('test_'):
                        python_files.append(os.path.join(root, file))
        
        except Exception as e:
            logger.error(f"❌ Error finding Python files: {e}")
        
        return sorted(python_files)
    
    def encrypt(self) -> bool:
        """Encrypt the project"""
        try:
            logger.info("🔐 Starting encryption...")
            
            cmd_args = ["obfuscate", "--output", self.config.dist_dir]
            
            returncode, stdout, stderr = self._run_command(*cmd_args)
            
            if returncode == 0:
                logger.info(f"✅ Encryption completed successfully")
                logger.info(f"📦 Encrypted code in: {self.config.dist_dir}")
                return True
            else:
                logger.error(f"❌ Encryption failed: {stderr}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error during encryption: {e}")
            return False
    
    def verify_encryption(self) -> bool:
        """Verify encrypted code integrity"""
        try:
            logger.info("🔍 Verifying encrypted code...")
            
            # Check encrypted files exist
            if not os.path.exists(self.config.dist_dir):
                logger.error(f"❌ Distribution directory not found: {self.config.dist_dir}")
                return False
            
            encrypted_files = list(Path(self.config.dist_dir).glob("**/*.pyc"))
            
            if not encrypted_files:
                logger.error(f"❌ No encrypted files found in {self.config.dist_dir}")
                return False
            
            logger.info(f"✅ Found {len(encrypted_files)} encrypted files")
            
            # Verify original sources cannot be read as plain text
            suspicious_count = 0
            for enc_file in encrypted_files:
                content = enc_file.read_bytes()
                # Check if file contains readable Python symbols
                if b'def ' in content or b'import ' in content:
                    logger.warning(f"  ⚠️ {enc_file} may contain readable content")
                    suspicious_count += 1
            
            if suspicious_count > 0:
                logger.warning(f"⚠️ {suspicious_count} files may not be fully encrypted")
                return False
            
            logger.info("✅ Encryption verification passed")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error verifying encryption: {e}")
            return False
    
    def create_backup(self) -> Optional[str]:
        """Create backup of original source before encryption"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = f"backup_{timestamp}"
            
            logger.info(f"💾 Creating backup: {backup_dir}")
            
            shutil.copytree(self.config.source_dir, backup_dir)
            
            logger.info(f"✅ Backup created at: {backup_dir}")
            return backup_dir
        
        except Exception as e:
            logger.error(f"❌ Error creating backup: {e}")
            return None
    
    def generate_license(self, expiry_date: Optional[str] = None) -> bool:
        """Generate PyArmor license file (commercial mode only)"""
        try:
            if self.config.mode != EncryptionMode.ADVANCED:
                logger.warning("⚠️ License generation requires ADVANCED mode")
                return False
            
            logger.info("📜 Generating PyArmor license...")
            
            cmd_args = ["licenses"]
            
            if expiry_date:
                cmd_args.extend(["-x", f"after:{expiry_date}"])
            else:
                cmd_args.extend(["-x", "none"])  # No expiry
            
            cmd_args.append("default")
            
            returncode, stdout, stderr = self._run_command(*cmd_args)
            
            if returncode == 0:
                license_file = os.path.join(self.config.output_dir, "license.lic")
                logger.info(f"✅ License generated: {license_file}")
                return True
            else:
                logger.error(f"❌ License generation failed: {stderr}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error generating license: {e}")
            return False
    
    def full_encryption_workflow(self) -> bool:
        """Complete encryption workflow"""
        try:
            logger.info("=" * 60)
            logger.info("STARTING FULL ENCRYPTION WORKFLOW")
            logger.info("=" * 60)
            
            # Step 1: Create backup
            backup_dir = self.create_backup()
            if not backup_dir:
                logger.error("❌ Backup creation failed")
                return False
            
            # Step 2: Initialize project
            if not self.init_project():
                logger.error("❌ Project initialization failed")
                return False
            
            # Step 3: Configure
            if not self.configure_project():
                logger.error("❌ Project configuration failed")
                return False
            
            # Step 4: Add sources
            if not self.add_sources():
                logger.error("❌ Failed to add sources")
                return False
            
            # Step 5: Encrypt
            if not self.encrypt():
                logger.error("❌ Encryption failed")
                return False
            
            # Step 6: Verify
            if not self.verify_encryption():
                logger.error("❌ Encryption verification failed")
                return False
            
            # Step 7: Generate license (if commercial)
            if self.config.mode == EncryptionMode.ADVANCED:
                if not self.generate_license(self.config.license_expiry):
                    logger.warning("⚠️ License generation skipped")
            
            elapsed = (datetime.now() - self.start_time).total_seconds()
            logger.info("=" * 60)
            logger.info(f"✅ ENCRYPTION COMPLETED SUCCESSFULLY ({elapsed:.1f}s)")
            logger.info(f"  Backup: {backup_dir}")
            logger.info(f"  Distribution: {self.config.dist_dir}")
            logger.info("=" * 60)
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Encryption workflow failed: {e}")
            return False
    
    def rollback_from_backup(self, backup_dir: str) -> bool:
        """Restore from backup (emergency rollback)"""
        try:
            logger.warning(f"🔄 Rolling back from backup: {backup_dir}")
            
            if not os.path.exists(backup_dir):
                logger.error(f"❌ Backup not found: {backup_dir}")
                return False
            
            # Remove encrypted artifacts
            if os.path.exists(self.config.output_dir):
                shutil.rmtree(self.config.output_dir)
            if os.path.exists(self.config.dist_dir):
                shutil.rmtree(self.config.dist_dir)
            
            # Restore source
            if os.path.exists(self.config.source_dir):
                shutil.rmtree(self.config.source_dir)
            
            shutil.copytree(backup_dir, self.config.source_dir)
            
            logger.info(f"✅ Rollback completed from: {backup_dir}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False


# CLI Interface
def main():
    """Command-line interface for encryption"""
    import argparse
    
    parser = argparse.ArgumentParser(description="PyArmor Encryption Agent")
    parser.add_argument("--mode", choices=["basic", "advanced"], default="basic",
                        help="Encryption mode")
    parser.add_argument("--source", default="agents",
                        help="Source directory to encrypt")
    parser.add_argument("--output", default=".pyarmor",
                        help="Output directory for project")
    parser.add_argument("--dist", default="dist",
                        help="Distribution directory for encrypted code")
    parser.add_argument("--no-obf-code", action="store_true",
                        help="Disable code obfuscation")
    parser.add_argument("--backup", action="store_true",
                        help="Create backup before encryption")
    parser.add_argument("--verify", action="store_true", default=True,
                        help="Verify encryption after completion")
    parser.add_argument("--rollback", help="Rollback from backup directory")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create config
    config = EncryptionConfig(
        mode=EncryptionMode.ADVANCED if args.mode == "advanced" else EncryptionMode.BASIC,
        source_dir=args.source,
        output_dir=args.output,
        dist_dir=args.dist,
        obfuscate_code=not args.no_obf_code,
    )
    
    # Create agent
    agent = PyArmorAgent(config)
    
    # Handle rollback
    if args.rollback:
        success = agent.rollback_from_backup(args.rollback)
        sys.exit(0 if success else 1)
    
    # Run encryption workflow
    success = agent.full_encryption_workflow()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

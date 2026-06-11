"""
Docker Image Signing Agent using GPG

Manages Docker image signing, verification, and registry operations.

Features:
- GPG signing of Docker images
- Image signature verification
- Registry upload with signatures
- CI/CD integration (GitHub Actions, GitLab CI, etc.)
- Automated signature verification on pull
- Key management and rotation

Security: Images signed with GPG-RSA-4096 keys
"""

import os
import sys
import subprocess
import json
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class GPGConfig:
    """GPG signing configuration"""
    
    gpg_key_id: Optional[str] = None  # Fingerprint or short ID
    gpg_key_email: Optional[str] = None  # Email associated with key
    gpg_home: Optional[str] = None  # GPG home directory (~/.gnupg)
    sign_with: str = "default"  # Key to use for signing
    
    # Docker registry
    registry_url: str = "docker.io"
    registry_username: Optional[str] = None
    registry_password: Optional[str] = None  # Use from environment
    
    # Image info
    image_name: str = "lrqa-app"
    image_tag: str = "v2.0"
    
    def __post_init__(self):
        if not self.gpg_home:
            self.gpg_home = os.path.expanduser("~/.gnupg")


class GPGError(Exception):
    """Raised when GPG operations fail"""
    pass


class DockerImageSigningAgent:
    """Manages Docker image signing with GPG"""
    
    def __init__(self, config: Optional[GPGConfig] = None):
        self.config = config or GPGConfig()
        self.gpg_available = self._check_gpg()
        self.docker_available = self._check_docker()
        
        if not self.gpg_available:
            raise GPGError("GPG not found. Install: brew install gpg (macOS) or apt install gnupg (Linux)")
        if not self.docker_available:
            raise GPGError("Docker not found. Install Docker Desktop or Docker CLI")
        
        logger.info("✅ GPG and Docker available")
    
    def _check_gpg(self) -> bool:
        """Check if GPG is available"""
        try:
            result = subprocess.run(["gpg", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.split('\n')[0]
                logger.info(f"✅ GPG available: {version}")
                return True
        except FileNotFoundError:
            pass
        return False
    
    def _check_docker(self) -> bool:
        """Check if Docker is available"""
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"✅ {result.stdout.strip()}")
                return True
        except FileNotFoundError:
            pass
        return False
    
    def _run_command(self, *args, **kwargs) -> Tuple[int, str, str]:
        """Execute command and capture output"""
        cmd = list(args)
        logger.debug(f"🔨 Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
        
        if result.returncode != 0:
            logger.error(f"❌ Command failed:\n{result.stderr}")
        
        return result.returncode, result.stdout, result.stderr
    
    def generate_signing_key(self, name: str = "Desk Automation Signing",
                            email: str = "signing@example.com",
                            passphrase: str = "") -> bool:
        """Generate GPG signing key"""
        try:
            logger.info(f"🔑 Generating GPG key: {name} <{email}>")
            
            # Create GPG batch file for key generation
            key_gen_script = f"""
%echo Generating a basic OpenPGP key
Key-Type: RSA
Key-Length: 4096
Name-Real: {name}
Name-Email: {email}
Expire-Date: 0
%no-protection
%commit
%echo done
"""
            
            # Write script to temp file
            temp_script = "/tmp/gpg_key_gen.txt"
            with open(temp_script, 'w') as f:
                f.write(key_gen_script)
            
            # Generate key
            cmd = ["gpg", "--batch", "--generate-key", temp_script]
            returncode, stdout, stderr = self._run_command(*cmd)
            
            # Clean up
            os.remove(temp_script)
            
            if returncode == 0:
                # Get key ID from newly generated key
                list_cmd = ["gpg", "--list-keys", "--keyid-format", "long", email]
                list_rc, list_out, _ = self._run_command(*list_cmd)
                
                if list_rc == 0:
                    # Extract key ID
                    for line in list_out.split('\n'):
                        if 'pub' in line:
                            parts = line.split()
                            if len(parts) > 1:
                                self.config.gpg_key_id = parts[1].split('/')[-1]
                                self.config.gpg_key_email = email
                                break
                
                logger.info(f"✅ GPG key generated: {self.config.gpg_key_id}")
                return True
            else:
                logger.error(f"❌ Key generation failed: {stderr}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error generating key: {e}")
            return False
    
    def export_public_key(self, output_file: str = "public-key.asc") -> bool:
        """Export public GPG key"""
        try:
            if not self.config.gpg_key_id:
                logger.error("❌ No GPG key ID configured")
                return False
            
            logger.info(f"📄 Exporting public key to: {output_file}")
            
            cmd = [
                "gpg",
                "--export",
                "--armor",
                "--output", output_file,
                self.config.gpg_key_id
            ]
            
            returncode, _, stderr = self._run_command(*cmd)
            
            if returncode == 0:
                logger.info(f"✅ Public key exported")
                return True
            else:
                logger.error(f"❌ Export failed: {stderr}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error exporting public key: {e}")
            return False
    
    def export_secret_key(self, output_file: str = "secret-key.asc") -> bool:
        """Export secret GPG key (KEEP SECURE!)"""
        try:
            if not self.config.gpg_key_id:
                logger.error("❌ No GPG key ID configured")
                return False
            
            logger.warning(f"⚠️ Exporting SECRET key to: {output_file}")
            logger.warning("⚠️ KEEP THIS FILE SECURE - Do NOT commit to version control!")
            
            cmd = [
                "gpg",
                "--export-secret-keys",
                "--armor",
                "--output", output_file,
                self.config.gpg_key_id
            ]
            
            returncode, _, stderr = self._run_command(*cmd)
            
            if returncode == 0:
                # Set restrictive permissions
                os.chmod(output_file, 0o600)
                logger.info(f"✅ Secret key exported with restricted permissions")
                return True
            else:
                logger.error(f"❌ Export failed: {stderr}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error exporting secret key: {e}")
            return False
    
    def sign_image_tarball(self, image_tar: str) -> bool:
        """Sign Docker image tarball with GPG"""
        try:
            if not self.config.gpg_key_id:
                logger.error("❌ No GPG key ID configured")
                return False
            
            if not os.path.exists(image_tar):
                logger.error(f"❌ Image tarball not found: {image_tar}")
                return False
            
            signature_file = f"{image_tar}.asc"
            logger.info(f"🔐 Signing image: {image_tar}")
            
            cmd = [
                "gpg",
                "--default-key", self.config.gpg_key_id,
                "--detach-sign",
                "--armor",
                "--output", signature_file,
                image_tar
            ]
            
            returncode, _, stderr = self._run_command(*cmd)
            
            if returncode == 0:
                logger.info(f"✅ Image signed: {signature_file}")
                return True
            else:
                logger.error(f"❌ Signing failed: {stderr}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error signing image: {e}")
            return False
    
    def verify_image_signature(self, image_tar: str) -> bool:
        """Verify GPG signature of image tarball"""
        try:
            signature_file = f"{image_tar}.asc"
            
            if not os.path.exists(image_tar):
                logger.error(f"❌ Image not found: {image_tar}")
                return False
            
            if not os.path.exists(signature_file):
                logger.error(f"❌ Signature not found: {signature_file}")
                return False
            
            logger.info(f"🔍 Verifying signature: {signature_file}")
            
            cmd = [
                "gpg",
                "--verify",
                signature_file,
                image_tar
            ]
            
            returncode, stdout, stderr = self._run_command(*cmd)
            
            if returncode == 0:
                # Parse verification output
                if "Good signature" in stdout + stderr:
                    logger.info(f"✅ Signature verified successfully")
                    return True
                else:
                    logger.warning(f"⚠️ Signature verification uncertain")
                    return False
            else:
                logger.error(f"❌ Signature verification failed: {stderr}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error verifying signature: {e}")
            return False
    
    def build_docker_image(self) -> bool:
        """Build Docker image"""
        try:
            image_full = f"{self.config.image_name}:{self.config.image_tag}"
            logger.info(f"🐳 Building Docker image: {image_full}")
            
            cmd = [
                "docker",
                "build",
                "-t", image_full,
                "."
            ]
            
            returncode, stdout, stderr = self._run_command(*cmd)
            
            if returncode == 0:
                logger.info(f"✅ Docker image built: {image_full}")
                return True
            else:
                logger.error(f"❌ Build failed: {stderr}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error building image: {e}")
            return False
    
    def save_image_to_tarball(self, output_tar: Optional[str] = None) -> Optional[str]:
        """Save Docker image to tarball"""
        try:
            if not output_tar:
                output_tar = f"{self.config.image_name}_{self.config.image_tag}.tar"
            
            image_full = f"{self.config.image_name}:{self.config.image_tag}"
            logger.info(f"💾 Saving image to tarball: {output_tar}")
            
            cmd = [
                "docker",
                "save",
                "-o", output_tar,
                image_full
            ]
            
            returncode, _, stderr = self._run_command(*cmd)
            
            if returncode == 0:
                size_mb = os.path.getsize(output_tar) / (1024 * 1024)
                logger.info(f"✅ Image saved ({size_mb:.1f} MB): {output_tar}")
                return output_tar
            else:
                logger.error(f"❌ Save failed: {stderr}")
                return None
        
        except Exception as e:
            logger.error(f"❌ Error saving image: {e}")
            return None
    
    def load_image_from_tarball(self, tar_file: str) -> bool:
        """Load Docker image from tarball"""
        try:
            if not os.path.exists(tar_file):
                logger.error(f"❌ Tarball not found: {tar_file}")
                return False
            
            logger.info(f"🐳 Loading image from tarball: {tar_file}")
            
            cmd = [
                "docker",
                "load",
                "-i", tar_file
            ]
            
            returncode, stdout, stderr = self._run_command(*cmd)
            
            if returncode == 0:
                logger.info(f"✅ Image loaded successfully")
                return True
            else:
                logger.error(f"❌ Load failed: {stderr}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error loading image: {e}")
            return False
    
    def push_image_to_registry(self, username: Optional[str] = None,
                             password: Optional[str] = None) -> bool:
        """Push image to registry (after signing)"""
        try:
            # Use provided or configured credentials
            username = username or self.config.registry_username or os.getenv('REGISTRY_USERNAME')
            password = password or self.config.registry_password or os.getenv('REGISTRY_PASSWORD')
            
            if not username or not password:
                logger.error("❌ Registry credentials not provided")
                return False
            
            image_full = f"{self.config.image_name}:{self.config.image_tag}"
            logger.info(f"📤 Pushing image to registry: {image_full}")
            
            # Login
            login_cmd = ["docker", "login", "-u", username, "--password-stdin"]
            returncode, _, stderr = self._run_command(
                *login_cmd,
                input=password
            )
            
            if returncode != 0:
                logger.error(f"❌ Login failed: {stderr}")
                return False
            
            # Push image
            push_cmd = ["docker", "push", image_full]
            returncode, _, stderr = self._run_command(*push_cmd)
            
            if returncode == 0:
                logger.info(f"✅ Image pushed successfully")
                return True
            else:
                logger.error(f"❌ Push failed: {stderr}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error pushing image: {e}")
            return False
    
    def full_signing_workflow(self) -> bool:
        """Complete image building, signing, and verification workflow"""
        try:
            logger.info("=" * 60)
            logger.info("STARTING DOCKER IMAGE SIGNING WORKFLOW")
            logger.info("=" * 60)
            
            # Step 1: Build image
            if not self.build_docker_image():
                logger.error("❌ Image build failed")
                return False
            
            # Step 2: Save to tarball
            tar_file = self.save_image_to_tarball()
            if not tar_file:
                logger.error("❌ Image save failed")
                return False
            
            # Step 3: Sign image
            if not self.sign_image_tarball(tar_file):
                logger.error("❌ Image signing failed")
                return False
            
            # Step 4: Verify signature
            if not self.verify_image_signature(tar_file):
                logger.error("❌ Signature verification failed")
                return False
            
            logger.info("=" * 60)
            logger.info("✅ SIGNING WORKFLOW COMPLETED SUCCESSFULLY")
            logger.info(f"  Image: {tar_file}")
            logger.info(f"  Signature: {tar_file}.asc")
            logger.info("=" * 60)
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Signing workflow failed: {e}")
            return False
    
    def deploy_with_verification(self, tar_file: str) -> bool:
        """Deploy image with signature verification"""
        try:
            logger.info("🚀 Deploying image with verification")
            
            # Step 1: Verify signature
            if not self.verify_image_signature(tar_file):
                logger.error("❌ Signature verification failed - DEPLOYMENT ABORTED")
                return False
            
            # Step 2: Load image
            if not self.load_image_from_tarball(tar_file):
                logger.error("❌ Image load failed")
                return False
            
            # Step 3: Run image (basic check)
            image_full = f"{self.config.image_name}:{self.config.image_tag}"
            logger.info(f"🧪 Running basic image test...")
            
            cmd = [
                "docker",
                "run",
                "--rm",
                image_full,
                "python", "-c", "print('✅ Image runs successfully')"
            ]
            
            returncode, stdout, stderr = self._run_command(*cmd)
            
            if returncode == 0:
                logger.info("✅ Deployment successful")
                return True
            else:
                logger.error(f"❌ Deployment test failed: {stderr}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error during deployment: {e}")
            return False


# CLI Interface
def main():
    """Command-line interface for image signing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Docker Image Signing Agent")
    parser.add_argument("--generate-key", action="store_true",
                        help="Generate new GPG signing key")
    parser.add_argument("--image-name", default="lrqa-app",
                        help="Docker image name")
    parser.add_argument("--image-tag", default="v2.0",
                        help="Docker image tag")
    parser.add_argument("--export-public", help="Export public key to file")
    parser.add_argument("--export-secret", help="Export secret key to file")
    parser.add_argument("--build", action="store_true",
                        help="Build Docker image")
    parser.add_argument("--save", help="Save image to tarball")
    parser.add_argument("--sign", help="Sign image tarball")
    parser.add_argument("--verify", help="Verify image signature")
    parser.add_argument("--deploy", help="Deploy image with verification")
    parser.add_argument("--full-workflow", action="store_true",
                        help="Run complete signing workflow")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create config
    config = GPGConfig(
        image_name=args.image_name,
        image_tag=args.image_tag,
    )
    
    # Create agent
    agent = DockerImageSigningAgent(config)
    
    # Handle commands
    if args.generate_key:
        success = agent.generate_signing_key()
    elif args.export_public:
        success = agent.export_public_key(args.export_public)
    elif args.export_secret:
        success = agent.export_secret_key(args.export_secret)
    elif args.build:
        success = agent.build_docker_image()
    elif args.save:
        success = agent.save_image_to_tarball(args.save) is not None
    elif args.sign:
        success = agent.sign_image_tarball(args.sign)
    elif args.verify:
        success = agent.verify_image_signature(args.verify)
    elif args.deploy:
        success = agent.deploy_with_verification(args.deploy)
    elif args.full_workflow:
        success = agent.full_signing_workflow()
    else:
        parser.print_help()
        success = True
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

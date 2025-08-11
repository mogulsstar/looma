"""Package signing module for Looma."""

import base64
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import nacl.encoding
import nacl.signing
import structlog

from looma.core.exceptions import SecurityError

logger = structlog.get_logger()


class SigningManager:
    """
    Manages package signing with Ed25519.
    
    Attributes
    ----------
    config : ConfigManager
        Configuration manager
    signing_key : Optional[nacl.signing.SigningKey]
        Signing key for creating signatures
    """
    
    def __init__(self, config):
        """
        Initialize signing manager.
        
        Parameters
        ----------
        config : ConfigManager
            Configuration manager
        """
        self.config = config
        self.signing_key = None
        
        # Load signing key if configured
        if config.get("security.signing.enabled"):
            self._load_signing_key()
    
    def _load_signing_key(self) -> None:
        """Load signing key from configuration."""
        private_key_path = self.config.get("security.signing.private_key_path")
        
        if not private_key_path:
            logger.warning("Signing enabled but no private key configured")
            return
        
        try:
            key_path = Path(private_key_path)
            if not key_path.exists():
                logger.error(f"Private key not found: {key_path}")
                return
            
            # Read key file
            key_content = key_path.read_text().strip()
            
            # Remove PEM headers if present
            if "BEGIN PRIVATE KEY" in key_content:
                lines = key_content.split("\n")
                key_content = "".join(lines[1:-1])
            
            # Decode base64
            if key_content.startswith("base64:"):
                key_content = key_content[7:]
            
            key_bytes = base64.b64decode(key_content)
            
            # Create signing key
            self.signing_key = nacl.signing.SigningKey(key_bytes)
            logger.info("Signing key loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load signing key: {e}")
            raise SecurityError(f"Failed to load signing key: {e}")
    
    def generate_keypair(self) -> Tuple[str, str]:
        """
        Generate new Ed25519 keypair.
        
        Returns
        -------
        tuple
            (private_key_base64, public_key_base64)
        """
        # Generate signing key
        signing_key = nacl.signing.SigningKey.generate()
        
        # Get verify key (public key)
        verify_key = signing_key.verify_key
        
        # Encode as base64
        private_key_b64 = base64.b64encode(bytes(signing_key)).decode()
        public_key_b64 = base64.b64encode(bytes(verify_key)).decode()
        
        logger.info("Generated new Ed25519 keypair")
        
        return private_key_b64, public_key_b64
    
    def save_keypair(self, private_key: str, public_key: str, key_dir: Path) -> None:
        """
        Save keypair to files.
        
        Parameters
        ----------
        private_key : str
            Base64-encoded private key
        public_key : str
            Base64-encoded public key
        key_dir : Path
            Directory to save keys
        """
        from looma.core.utils import ensure_dir
        
        ensure_dir(key_dir)
        
        # Save private key
        private_key_path = key_dir / "private.key"
        private_key_path.write_text(f"base64:{private_key}")
        private_key_path.chmod(0o600)  # Restrict permissions
        
        # Save public key
        public_key_path = key_dir / "public.key"
        public_key_path.write_text(f"base64:{public_key}")
        
        logger.info(f"Keypair saved to {key_dir}")
    
    def sign_package(self, package_path: Path) -> str:
        """
        Sign a package file.
        
        Parameters
        ----------
        package_path : Path
            Path to package file
            
        Returns
        -------
        str
            Base64-encoded signature
            
        Raises
        ------
        SecurityError
            If signing fails
        """
        if not self.signing_key:
            raise SecurityError("No signing key loaded")
        
        try:
            # Read package data
            package_data = package_path.read_bytes()
            
            # Sign package
            signed = self.signing_key.sign(package_data)
            
            # Return signature only
            signature = signed.signature
            signature_b64 = base64.b64encode(signature).decode()
            
            logger.info(f"Signed package: {package_path.name}")
            
            return f"base64:{signature_b64}"
            
        except Exception as e:
            raise SecurityError(f"Failed to sign package: {e}")
    
    def sign_manifest(self, manifest: Dict[str, Any]) -> str:
        """
        Sign a manifest dictionary.
        
        Parameters
        ----------
        manifest : dict
            Manifest data
            
        Returns
        -------
        str
            Base64-encoded signature
            
        Raises
        ------
        SecurityError
            If signing fails
        """
        if not self.signing_key:
            raise SecurityError("No signing key loaded")
        
        try:
            # Serialize manifest (sorted for consistency)
            manifest_json = json.dumps(manifest, sort_keys=True)
            manifest_bytes = manifest_json.encode("utf-8")
            
            # Sign manifest
            signed = self.signing_key.sign(manifest_bytes)
            
            # Return signature only
            signature = signed.signature
            signature_b64 = base64.b64encode(signature).decode()
            
            logger.info("Signed manifest")
            
            return f"base64:{signature_b64}"
            
        except Exception as e:
            raise SecurityError(f"Failed to sign manifest: {e}")
    
    def create_signed_manifest(self, files: List[Path]) -> Dict[str, Any]:
        """
        Create a signed manifest for multiple files.
        
        Parameters
        ----------
        files : List[Path]
            List of file paths
            
        Returns
        -------
        dict
            Signed manifest with file hashes and signatures
        """
        from looma.core.utils import calculate_hash, get_file_size
        
        manifest = {
            "version": "1.0",
            "files": {},
        }
        
        for file_path in files:
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                continue
            
            file_info = {
                "size": get_file_size(file_path),
                "hash": calculate_hash(file_path),
            }
            
            # Sign individual file if key is available
            if self.signing_key:
                file_info["signature"] = self.sign_package(file_path)
            
            manifest["files"][file_path.name] = file_info
        
        # Sign the entire manifest
        if self.signing_key:
            manifest["signature"] = self.sign_manifest(manifest)
        
        return manifest
    
    def verify_signature(self, data: bytes, signature: str, public_key: str) -> bool:
        """
        Verify a signature.
        
        Parameters
        ----------
        data : bytes
            Data that was signed
        signature : str
            Base64-encoded signature
        public_key : str
            Base64-encoded public key
            
        Returns
        -------
        bool
            True if signature is valid
        """
        try:
            # Decode signature
            if signature.startswith("base64:"):
                signature = signature[7:]
            sig_bytes = base64.b64decode(signature)
            
            # Decode public key
            if public_key.startswith("base64:"):
                public_key = public_key[7:]
            key_bytes = base64.b64decode(public_key)
            
            # Create verify key
            verify_key = nacl.signing.VerifyKey(key_bytes)
            
            # Verify signature
            verify_key.verify(data, sig_bytes)
            
            return True
            
        except nacl.exceptions.BadSignatureError:
            return False
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False


# Alias for backward compatibility
Signer = SigningManager
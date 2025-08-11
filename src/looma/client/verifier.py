"""Signature verification for Looma update packages."""

import base64
from pathlib import Path
from typing import List, Optional

import nacl.encoding
import nacl.signing
import structlog

from looma.core.exceptions import SecurityError

logger = structlog.get_logger()


class SignatureVerifier:
    """
    Verifies package signatures using Ed25519.
    
    Attributes
    ----------
    config : ConfigManager
        Configuration manager
    trusted_keys : List[nacl.signing.VerifyKey]
        List of trusted public keys
    """
    
    def __init__(self, config):
        """
        Initialize signature verifier.
        
        Parameters
        ----------
        config : ConfigManager
            Configuration manager
        """
        self.config = config
        self.trusted_keys = self._load_trusted_keys()
    
    def _load_trusted_keys(self) -> List[nacl.signing.VerifyKey]:
        """
        Load trusted public keys.
        
        Returns
        -------
        List[nacl.signing.VerifyKey]
            List of trusted verify keys
        """
        keys = []
        
        # Load main public key
        public_key_str = self.config.get("security.signing.public_key")
        if public_key_str:
            try:
                key = self._parse_public_key(public_key_str)
                if key:
                    keys.append(key)
            except Exception as e:
                logger.warning(f"Failed to load main public key: {e}")
        
        # Load additional trusted keys
        trusted_key_paths = self.config.get("security.verification.trusted_keys", [])
        for key_path in trusted_key_paths:
            try:
                key = self._load_key_from_file(key_path)
                if key:
                    keys.append(key)
            except Exception as e:
                logger.warning(f"Failed to load trusted key from {key_path}: {e}")
        
        return keys
    
    def _parse_public_key(self, key_str: str) -> Optional[nacl.signing.VerifyKey]:
        """
        Parse public key from string.
        
        Parameters
        ----------
        key_str : str
            Public key string (base64 or PEM format)
            
        Returns
        -------
        Optional[nacl.signing.VerifyKey]
            Verify key or None
        """
        try:
            # Remove PEM headers if present
            if "BEGIN PUBLIC KEY" in key_str:
                lines = key_str.strip().split("\n")
                key_str = "".join(lines[1:-1])
            
            # Decode base64
            if key_str.startswith("base64:"):
                key_str = key_str[7:]
            
            key_bytes = base64.b64decode(key_str)
            
            # Create verify key
            return nacl.signing.VerifyKey(key_bytes)
            
        except Exception as e:
            logger.error(f"Failed to parse public key: {e}")
            return None
    
    def _load_key_from_file(self, key_path: str) -> Optional[nacl.signing.VerifyKey]:
        """
        Load public key from file.
        
        Parameters
        ----------
        key_path : str
            Path to key file
            
        Returns
        -------
        Optional[nacl.signing.VerifyKey]
            Verify key or None
        """
        try:
            path = Path(key_path)
            if not path.exists():
                logger.warning(f"Key file not found: {key_path}")
                return None
            
            key_content = path.read_text()
            return self._parse_public_key(key_content)
            
        except Exception as e:
            logger.error(f"Failed to load key from {key_path}: {e}")
            return None
    
    def verify_package(
        self,
        package_path: Path,
        signature: str,
        public_key: Optional[str] = None,
    ) -> bool:
        """
        Verify package signature.
        
        Parameters
        ----------
        package_path : Path
            Path to package file
        signature : str
            Base64-encoded signature
        public_key : Optional[str]
            Public key to use (if not using trusted keys)
            
        Returns
        -------
        bool
            True if signature is valid
        """
        try:
            # Read package data
            package_data = package_path.read_bytes()
            
            # Decode signature
            if signature.startswith("base64:"):
                signature = signature[7:]
            sig_bytes = base64.b64decode(signature)
            
            # Get verify keys
            verify_keys = []
            if public_key:
                key = self._parse_public_key(public_key)
                if key:
                    verify_keys.append(key)
            else:
                verify_keys = self.trusted_keys
            
            if not verify_keys:
                logger.error("No public keys available for verification")
                return False
            
            # Try to verify with each key
            for verify_key in verify_keys:
                try:
                    verify_key.verify(package_data, sig_bytes)
                    logger.info("Package signature verified successfully")
                    return True
                except nacl.exceptions.BadSignatureError:
                    continue
            
            logger.error("Package signature verification failed")
            return False
            
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False
    
    def verify_manifest(self, manifest: dict) -> bool:
        """
        Verify manifest integrity.
        
        Parameters
        ----------
        manifest : dict
            Manifest data with signatures
            
        Returns
        -------
        bool
            True if manifest is valid
        """
        try:
            # Extract manifest signature
            signature = manifest.get("signature")
            if not signature:
                logger.error("Manifest signature missing")
                return False
            
            # Remove signature from manifest for verification
            manifest_copy = manifest.copy()
            del manifest_copy["signature"]
            
            # Serialize manifest
            import json
            manifest_data = json.dumps(manifest_copy, sort_keys=True).encode()
            
            # Decode signature
            if signature.startswith("base64:"):
                signature = signature[7:]
            sig_bytes = base64.b64decode(signature)
            
            # Verify with trusted keys
            for verify_key in self.trusted_keys:
                try:
                    verify_key.verify(manifest_data, sig_bytes)
                    logger.info("Manifest signature verified successfully")
                    return True
                except nacl.exceptions.BadSignatureError:
                    continue
            
            logger.error("Manifest signature verification failed")
            return False
            
        except Exception as e:
            logger.error(f"Manifest verification error: {e}")
            return False
    
    def generate_keypair(self) -> tuple:
        """
        Generate new Ed25519 keypair.
        
        Returns
        -------
        tuple
            (private_key_base64, public_key_base64)
        """
        # Generate signing key (contains private key)
        signing_key = nacl.signing.SigningKey.generate()
        
        # Get verify key (public key)
        verify_key = signing_key.verify_key
        
        # Encode as base64
        private_key_b64 = base64.b64encode(bytes(signing_key)).decode()
        public_key_b64 = base64.b64encode(bytes(verify_key)).decode()
        
        return private_key_b64, public_key_b64
    
    def sign_package(self, package_path: Path, private_key: str) -> str:
        """
        Sign a package.
        
        Parameters
        ----------
        package_path : Path
            Path to package file
        private_key : str
            Base64-encoded private key
            
        Returns
        -------
        str
            Base64-encoded signature
            
        Raises
        ------
        SecurityError
            If signing fails
        """
        try:
            # Decode private key
            if private_key.startswith("base64:"):
                private_key = private_key[7:]
            key_bytes = base64.b64decode(private_key)
            
            # Create signing key
            signing_key = nacl.signing.SigningKey(key_bytes)
            
            # Read package data
            package_data = package_path.read_bytes()
            
            # Sign package
            signed = signing_key.sign(package_data)
            
            # Return signature only (not the message)
            signature = signed.signature
            return "base64:" + base64.b64encode(signature).decode()
            
        except Exception as e:
            raise SecurityError(f"Failed to sign package: {e}")
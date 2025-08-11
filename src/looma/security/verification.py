"""Verification module for Looma security."""

import base64
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import nacl.signing
import structlog

from looma.core.exceptions import SecurityError
from looma.core.utils import calculate_hash

logger = structlog.get_logger()


class Verifier:
    """
    Verifies signatures and integrity of packages.
    
    Attributes
    ----------
    config : ConfigManager
        Configuration manager
    trusted_keys : List[nacl.signing.VerifyKey]
        List of trusted public keys
    """
    
    def __init__(self, config):
        """
        Initialize verifier.
        
        Parameters
        ----------
        config : ConfigManager
            Configuration manager
        """
        self.config = config
        self.trusted_keys = self._load_trusted_keys()
        self.strict_mode = config.get("security.verification.strict", True)
    
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
        
        if not keys:
            logger.warning("No trusted keys loaded for verification")
        
        return keys
    
    def _parse_public_key(self, key_str: str) -> Optional[nacl.signing.VerifyKey]:
        """
        Parse public key from string.
        
        Parameters
        ----------
        key_str : str
            Public key string
            
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
            Public key to use
            
        Returns
        -------
        bool
            True if signature is valid
            
        Raises
        ------
        SecurityError
            If strict mode and verification fails
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
                error_msg = "No public keys available for verification"
                logger.error(error_msg)
                if self.strict_mode:
                    raise SecurityError(error_msg)
                return False
            
            # Try to verify with each key
            for verify_key in verify_keys:
                try:
                    verify_key.verify(package_data, sig_bytes)
                    logger.info(f"Package signature verified: {package_path.name}")
                    return True
                except nacl.exceptions.BadSignatureError:
                    continue
            
            error_msg = f"Package signature verification failed: {package_path.name}"
            logger.error(error_msg)
            
            if self.strict_mode:
                raise SecurityError(error_msg)
            
            return False
            
        except SecurityError:
            raise
        except Exception as e:
            error_msg = f"Signature verification error: {e}"
            logger.error(error_msg)
            
            if self.strict_mode:
                raise SecurityError(error_msg)
            
            return False
    
    def verify_manifest(self, manifest: Dict[str, Any]) -> bool:
        """
        Verify manifest signature and integrity.
        
        Parameters
        ----------
        manifest : dict
            Manifest with signature
            
        Returns
        -------
        bool
            True if manifest is valid
        """
        try:
            # Extract signature
            signature = manifest.get("signature")
            if not signature:
                if self.strict_mode:
                    raise SecurityError("Manifest signature missing")
                return False
            
            # Create manifest copy without signature
            manifest_copy = manifest.copy()
            del manifest_copy["signature"]
            
            # Serialize manifest
            manifest_json = json.dumps(manifest_copy, sort_keys=True)
            manifest_bytes = manifest_json.encode("utf-8")
            
            # Decode signature
            if signature.startswith("base64:"):
                signature = signature[7:]
            sig_bytes = base64.b64decode(signature)
            
            # Verify with trusted keys
            for verify_key in self.trusted_keys:
                try:
                    verify_key.verify(manifest_bytes, sig_bytes)
                    logger.info("Manifest signature verified")
                    return True
                except nacl.exceptions.BadSignatureError:
                    continue
            
            error_msg = "Manifest signature verification failed"
            logger.error(error_msg)
            
            if self.strict_mode:
                raise SecurityError(error_msg)
            
            return False
            
        except SecurityError:
            raise
        except Exception as e:
            error_msg = f"Manifest verification error: {e}"
            logger.error(error_msg)
            
            if self.strict_mode:
                raise SecurityError(error_msg)
            
            return False
    
    def verify_file_integrity(self, file_path: Path, expected_hash: str) -> bool:
        """
        Verify file integrity using hash.
        
        Parameters
        ----------
        file_path : Path
            Path to file
        expected_hash : str
            Expected hash value
            
        Returns
        -------
        bool
            True if hash matches
        """
        try:
            # Parse hash format (algorithm:hash)
            if ":" in expected_hash:
                algorithm, hash_value = expected_hash.split(":", 1)
            else:
                algorithm = "sha256"
                hash_value = expected_hash
            
            # Calculate actual hash
            actual_hash = calculate_hash(file_path, algorithm)
            
            # Compare hashes
            match = actual_hash.lower() == hash_value.lower()
            
            if match:
                logger.info(f"File integrity verified: {file_path.name}")
            else:
                logger.error(f"File integrity check failed: {file_path.name}")
                if self.strict_mode:
                    raise SecurityError(f"File hash mismatch: {file_path.name}")
            
            return match
            
        except Exception as e:
            error_msg = f"File integrity verification error: {e}"
            logger.error(error_msg)
            
            if self.strict_mode:
                raise SecurityError(error_msg)
            
            return False
    
    def verify_update_package(
        self,
        package_path: Path,
        update_info: Dict[str, Any],
    ) -> bool:
        """
        Verify update package completely.
        
        Parameters
        ----------
        package_path : Path
            Path to update package
        update_info : dict
            Update information with hash and signature
            
        Returns
        -------
        bool
            True if package is valid
        """
        # Verify hash
        if "hash" in update_info:
            if not self.verify_file_integrity(package_path, update_info["hash"]):
                return False
        
        # Verify signature
        if "signature" in update_info:
            if not self.verify_package(package_path, update_info["signature"]):
                return False
        elif self.strict_mode:
            raise SecurityError("Update package signature missing")
        
        logger.info(f"Update package verified: {package_path.name}")
        return True
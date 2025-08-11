"""Certificate management for Looma."""

import ssl
from pathlib import Path
from typing import Optional

import structlog

from looma.core.exceptions import SecurityError

logger = structlog.get_logger()


class CertificateManager:
    """
    Manages SSL/TLS certificates for secure connections.
    
    Attributes
    ----------
    config : ConfigManager
        Configuration manager
    """
    
    def __init__(self, config):
        """
        Initialize certificate manager.
        
        Parameters
        ----------
        config : ConfigManager
            Configuration manager
        """
        self.config = config
        self.verify_ssl = config.get("security.ssl.verify", True)
        self.ca_bundle = config.get("security.ssl.ca_bundle")
        self.client_cert = config.get("security.ssl.client_cert")
        self.client_key = config.get("security.ssl.client_key")
        self.allow_self_signed = config.get("security.verification.allow_self_signed", False)
    
    def create_ssl_context(self) -> ssl.SSLContext:
        """
        Create SSL context with configured settings.
        
        Returns
        -------
        ssl.SSLContext
            Configured SSL context
            
        Raises
        ------
        SecurityError
            If SSL configuration is invalid
        """
        try:
            # Create SSL context
            context = ssl.create_default_context()
            
            # Configure verification
            if not self.verify_ssl:
                # Disable SSL verification (not recommended)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                logger.warning("SSL verification disabled")
            else:
                context.check_hostname = True
                context.verify_mode = ssl.CERT_REQUIRED
            
            # Set custom CA bundle
            if self.ca_bundle:
                ca_path = Path(self.ca_bundle)
                if not ca_path.exists():
                    raise SecurityError(f"CA bundle not found: {ca_path}")
                
                if ca_path.is_file():
                    context.load_verify_locations(cafile=str(ca_path))
                else:
                    context.load_verify_locations(capath=str(ca_path))
                
                logger.info(f"Using custom CA bundle: {ca_path}")
            
            # Set client certificate
            if self.client_cert:
                cert_path = Path(self.client_cert)
                if not cert_path.exists():
                    raise SecurityError(f"Client certificate not found: {cert_path}")
                
                if self.client_key:
                    key_path = Path(self.client_key)
                    if not key_path.exists():
                        raise SecurityError(f"Client key not found: {key_path}")
                    
                    context.load_cert_chain(str(cert_path), str(key_path))
                else:
                    context.load_cert_chain(str(cert_path))
                
                logger.info("Client certificate loaded")
            
            # Allow self-signed certificates if configured
            if self.allow_self_signed and self.verify_ssl:
                # This is a simplified approach
                # In production, you'd want more sophisticated handling
                context.check_hostname = False
                logger.warning("Self-signed certificates allowed")
            
            return context
            
        except Exception as e:
            raise SecurityError(f"Failed to create SSL context: {e}")
    
    def get_httpx_verify(self):
        """
        Get verification setting for httpx client.
        
        Returns
        -------
        bool or str
            False to disable, True for default, or path to CA bundle
        """
        if not self.verify_ssl:
            return False
        elif self.ca_bundle:
            return self.ca_bundle
        else:
            return True
    
    def get_httpx_cert(self) -> Optional[tuple]:
        """
        Get client certificate for httpx client.
        
        Returns
        -------
        Optional[tuple]
            (cert, key) tuple or None
        """
        if self.client_cert:
            if self.client_key:
                return (self.client_cert, self.client_key)
            else:
                return self.client_cert
        return None
    
    def validate_certificate(self, cert_path: Path) -> bool:
        """
        Validate a certificate file.
        
        Parameters
        ----------
        cert_path : Path
            Path to certificate file
            
        Returns
        -------
        bool
            True if certificate is valid
        """
        try:
            import cryptography.x509
            from cryptography.hazmat.backends import default_backend
            
            # Read certificate
            with open(cert_path, "rb") as f:
                cert_data = f.read()
            
            # Try to load as PEM
            try:
                cert = cryptography.x509.load_pem_x509_certificate(
                    cert_data,
                    default_backend()
                )
            except Exception:
                # Try to load as DER
                cert = cryptography.x509.load_der_x509_certificate(
                    cert_data,
                    default_backend()
                )
            
            # Check if certificate is expired
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            
            if cert.not_valid_after < now:
                logger.warning(f"Certificate expired: {cert_path}")
                return False
            
            if cert.not_valid_before > now:
                logger.warning(f"Certificate not yet valid: {cert_path}")
                return False
            
            logger.info(f"Certificate valid: {cert_path}")
            return True
            
        except Exception as e:
            logger.error(f"Certificate validation error: {e}")
            return False
    
    def extract_certificate_info(self, cert_path: Path) -> dict:
        """
        Extract information from a certificate.
        
        Parameters
        ----------
        cert_path : Path
            Path to certificate file
            
        Returns
        -------
        dict
            Certificate information
        """
        try:
            import cryptography.x509
            from cryptography.hazmat.backends import default_backend
            
            # Read certificate
            with open(cert_path, "rb") as f:
                cert_data = f.read()
            
            # Try to load certificate
            try:
                cert = cryptography.x509.load_pem_x509_certificate(
                    cert_data,
                    default_backend()
                )
            except Exception:
                cert = cryptography.x509.load_der_x509_certificate(
                    cert_data,
                    default_backend()
                )
            
            # Extract information
            info = {
                "subject": str(cert.subject),
                "issuer": str(cert.issuer),
                "serial_number": str(cert.serial_number),
                "not_before": cert.not_valid_before.isoformat(),
                "not_after": cert.not_valid_after.isoformat(),
                "signature_algorithm": str(cert.signature_algorithm_oid),
                "version": cert.version.name,
            }
            
            # Extract SANs if present
            try:
                san_ext = cert.extensions.get_extension_for_oid(
                    cryptography.x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
                )
                sans = []
                for san in san_ext.value:
                    sans.append(san.value)
                info["subject_alternative_names"] = sans
            except Exception:
                pass
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to extract certificate info: {e}")
            return {}
"""Key management commands for Looma CLI."""

import sys
from pathlib import Path
from typing import Optional

import click
import structlog

logger = structlog.get_logger()


@click.group()
def keys():
    """Manage signing keys."""
    pass


@keys.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="keys",
    help="Output directory for keys",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing keys",
)
@click.pass_context
def generate(ctx, output: str, force: bool):
    """Generate new signing keypair."""
    from looma.security.signing import Signer
    
    output_dir = Path(output)
    private_key_path = output_dir / "private.key"
    public_key_path = output_dir / "public.key"
    
    # Check if keys already exist
    if not force and (private_key_path.exists() or public_key_path.exists()):
        click.echo("Keys already exist. Use --force to overwrite.", err=True)
        sys.exit(1)
    
    try:
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate keypair
        signer = Signer({})
        private_key, public_key = signer.generate_keypair()
        
        # Save keys
        private_key_path.write_text(private_key)
        public_key_path.write_text(public_key)
        
        # Set permissions (Unix-like systems)
        import os
        import stat
        
        if hasattr(os, "chmod"):
            os.chmod(private_key_path, stat.S_IRUSR | stat.S_IWUSR)
        
        click.echo(f"Keypair generated:")
        click.echo(f"  Private key: {private_key_path}")
        click.echo(f"  Public key:  {public_key_path}")
        click.echo()
        click.echo("IMPORTANT: Keep the private key secure and never share it!")
        click.echo("Share the public key with users for signature verification.")
        
    except Exception as e:
        click.echo(f"Failed to generate keypair: {e}", err=True)
        sys.exit(1)


@keys.command()
@click.argument("package", type=click.Path(exists=True))
@click.option(
    "--key",
    "-k",
    type=click.Path(exists=True),
    help="Private key file",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output signature file",
)
@click.pass_context
def sign(ctx, package: str, key: Optional[str], output: Optional[str]):
    """Sign a package."""
    from looma.core.config import ConfigManager
    from looma.security.signing import Signer
    
    config_path = ctx.obj.get("config_path")
    package_path = Path(package)
    
    # Determine signature output path
    if output:
        sig_path = Path(output)
    else:
        sig_path = package_path.with_suffix(package_path.suffix + ".sig")
    
    try:
        # Load configuration
        config = {}
        if config_path.exists():
            config_manager = ConfigManager(config_path)
            config = config_manager.load()
        
        # Override key path if provided
        if key:
            if "security" not in config:
                config["security"] = {}
            if "signing" not in config["security"]:
                config["security"]["signing"] = {}
            config["security"]["signing"]["private_key_path"] = key
        
        # Create signer
        signer = Signer(config)
        
        # Sign package
        signature = signer.sign_package(package_path)
        
        # Save signature
        sig_path.write_text(signature)
        
        click.echo(f"Package signed: {package_path}")
        click.echo(f"Signature saved: {sig_path}")
        
    except Exception as e:
        click.echo(f"Failed to sign package: {e}", err=True)
        sys.exit(1)


@keys.command()
@click.argument("package", type=click.Path(exists=True))
@click.argument("signature", type=click.Path(exists=True))
@click.option(
    "--key",
    "-k",
    type=click.Path(exists=True),
    help="Public key file",
)
@click.pass_context
def verify(ctx, package: str, signature: str, key: Optional[str]):
    """Verify package signature."""
    from looma.core.config import ConfigManager
    from looma.security.verification import Verifier
    
    config_path = ctx.obj.get("config_path")
    package_path = Path(package)
    sig_path = Path(signature)
    
    try:
        # Load configuration
        config = {}
        if config_path.exists():
            config_manager = ConfigManager(config_path)
            config = config_manager.load()
        
        # Read signature
        signature_data = sig_path.read_text()
        
        # Read public key if provided
        public_key = None
        if key:
            public_key = Path(key).read_text()
        
        # Create verifier
        verifier = Verifier(config)
        
        # Verify package
        is_valid = verifier.verify_package(package_path, signature_data, public_key)
        
        if is_valid:
            click.echo("Signature verified successfully")
        else:
            click.echo("Signature verification failed", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Failed to verify signature: {e}", err=True)
        sys.exit(1)


@keys.command()
@click.argument("key_file", type=click.Path(exists=True))
@click.pass_context
def info(ctx, key_file: str):
    """Show key information."""
    import base64
    import nacl.signing
    
    key_path = Path(key_file)
    
    try:
        # Read key file
        key_content = key_path.read_text().strip()
        
        # Remove PEM headers if present
        if "BEGIN" in key_content:
            lines = key_content.split("\n")
            key_content = "".join([
                line for line in lines
                if not line.startswith("-----")
            ])
        
        # Decode base64
        if key_content.startswith("base64:"):
            key_content = key_content[7:]
        
        key_bytes = base64.b64decode(key_content)
        
        # Determine key type
        key_type = "Unknown"
        key_length = len(key_bytes)
        
        if key_length == 32:
            # Ed25519 public key
            key_type = "Ed25519 Public Key"
            try:
                verify_key = nacl.signing.VerifyKey(key_bytes)
                key_hex = verify_key.encode().hex()
            except Exception:
                key_hex = key_bytes.hex()
        elif key_length == 64:
            # Ed25519 private key
            key_type = "Ed25519 Private Key"
            try:
                signing_key = nacl.signing.SigningKey(key_bytes[:32])
                key_hex = signing_key.encode().hex()
                public_hex = signing_key.verify_key.encode().hex()
            except Exception:
                key_hex = key_bytes.hex()
                public_hex = None
        else:
            key_hex = key_bytes.hex()
        
        # Display information
        click.echo(f"Key File: {key_path}")
        click.echo(f"Key Type: {key_type}")
        click.echo(f"Key Size: {key_length} bytes")
        click.echo(f"Key (hex): {key_hex[:32]}...")
        
        if key_type == "Ed25519 Private Key" and public_hex:
            click.echo(f"Public Key (hex): {public_hex[:32]}...")
        
    except Exception as e:
        click.echo(f"Failed to read key information: {e}", err=True)
        sys.exit(1)


@keys.command()
@click.argument("private_key", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output public key file",
)
@click.pass_context
def export_public(ctx, private_key: str, output: Optional[str]):
    """Export public key from private key."""
    import base64
    import nacl.signing
    
    private_key_path = Path(private_key)
    
    if output:
        public_key_path = Path(output)
    else:
        public_key_path = private_key_path.parent / "public.key"
    
    try:
        # Read private key
        private_key_content = private_key_path.read_text().strip()
        
        # Remove PEM headers if present
        if "BEGIN" in private_key_content:
            lines = private_key_content.split("\n")
            private_key_content = "".join([
                line for line in lines
                if not line.startswith("-----")
            ])
        
        # Decode base64
        if private_key_content.startswith("base64:"):
            private_key_content = private_key_content[7:]
        
        private_key_bytes = base64.b64decode(private_key_content)
        
        # Create signing key
        if len(private_key_bytes) == 64:
            # Full keypair
            signing_key = nacl.signing.SigningKey(private_key_bytes[:32])
        else:
            # Just private key
            signing_key = nacl.signing.SigningKey(private_key_bytes)
        
        # Get public key
        public_key = signing_key.verify_key
        public_key_b64 = base64.b64encode(public_key.encode()).decode()
        
        # Format public key
        public_key_pem = f"""-----BEGIN PUBLIC KEY-----
{public_key_b64}
-----END PUBLIC KEY-----"""
        
        # Save public key
        public_key_path.write_text(public_key_pem)
        
        click.echo(f"Public key exported: {public_key_path}")
        
    except Exception as e:
        click.echo(f"Failed to export public key: {e}", err=True)
        sys.exit(1)
"""Verification commands for Looma CLI."""

import sys
from pathlib import Path
from typing import Optional

import click
import structlog

logger = structlog.get_logger()


@click.command()
@click.argument("package", type=click.Path(exists=True))
@click.option(
    "--signature",
    "-s",
    type=click.Path(exists=True),
    help="Signature file",
)
@click.option(
    "--hash",
    "-h",
    help="Expected hash value",
)
@click.option(
    "--algorithm",
    "-a",
    type=click.Choice(["sha256", "sha512", "md5"]),
    default="sha256",
    help="Hash algorithm",
)
@click.option(
    "--public-key",
    "-k",
    type=click.Path(exists=True),
    help="Public key for verification",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Enable strict verification",
)
@click.pass_context
def verify(
    ctx,
    package: str,
    signature: Optional[str],
    hash: Optional[str],
    algorithm: str,
    public_key: Optional[str],
    strict: bool,
):
    """Verify package integrity and signature."""
    from looma.core.config import ConfigManager
    from looma.core.utils import calculate_hash
    from looma.security.verification import Verifier
    
    config_path = ctx.obj.get("config_path")
    verbose = ctx.obj.get("verbose")
    package_path = Path(package)
    
    # Load configuration
    config = {}
    if config_path.exists():
        try:
            config_manager = ConfigManager(config_path)
            config = config_manager.load()
        except Exception as e:
            if verbose:
                click.echo(f"Warning: Failed to load configuration: {e}", err=True)
    
    # Override strict mode if specified
    if strict:
        if "security" not in config:
            config["security"] = {}
        if "verification" not in config["security"]:
            config["security"]["verification"] = {}
        config["security"]["verification"]["strict"] = True
    
    verification_passed = True
    
    # Verify hash if provided
    if hash:
        click.echo(f"Verifying {algorithm} hash...")
        
        actual_hash = calculate_hash(package_path, algorithm)
        
        # Normalize hash comparison
        expected_hash = hash.lower()
        if ":" in expected_hash:
            # Format: algorithm:hash
            _, expected_hash = expected_hash.split(":", 1)
        
        if actual_hash.lower() == expected_hash:
            click.echo(f"  Hash verification: PASSED")
            if verbose:
                click.echo(f"  Expected: {expected_hash}")
                click.echo(f"  Actual:   {actual_hash.lower()}")
        else:
            click.echo(f"  Hash verification: FAILED", err=True)
            click.echo(f"  Expected: {expected_hash}", err=True)
            click.echo(f"  Actual:   {actual_hash.lower()}", err=True)
            verification_passed = False
    
    # Verify signature if provided
    if signature:
        click.echo("Verifying signature...")
        
        sig_path = Path(signature)
        if not sig_path.exists():
            click.echo(f"  Signature file not found: {sig_path}", err=True)
            sys.exit(1)
        
        # Read signature
        signature_data = sig_path.read_text()
        
        # Read public key if provided
        public_key_data = None
        if public_key:
            key_path = Path(public_key)
            if not key_path.exists():
                click.echo(f"  Public key file not found: {key_path}", err=True)
                sys.exit(1)
            public_key_data = key_path.read_text()
        
        # Create verifier
        verifier = Verifier(config)
        
        try:
            # Verify signature
            is_valid = verifier.verify_package(
                package_path,
                signature_data,
                public_key_data,
            )
            
            if is_valid:
                click.echo(f"  Signature verification: PASSED")
            else:
                click.echo(f"  Signature verification: FAILED", err=True)
                verification_passed = False
                
        except Exception as e:
            click.echo(f"  Signature verification error: {e}", err=True)
            verification_passed = False
    
    # Auto-detect signature file if not provided
    elif not signature and not hash:
        # Look for .sig file
        sig_path = package_path.with_suffix(package_path.suffix + ".sig")
        if sig_path.exists():
            click.echo("Found signature file, verifying...")
            
            signature_data = sig_path.read_text()
            
            # Create verifier
            verifier = Verifier(config)
            
            try:
                is_valid = verifier.verify_package(package_path, signature_data)
                
                if is_valid:
                    click.echo(f"  Signature verification: PASSED")
                else:
                    click.echo(f"  Signature verification: FAILED", err=True)
                    verification_passed = False
                    
            except Exception as e:
                click.echo(f"  Signature verification error: {e}", err=True)
                verification_passed = False
        else:
            click.echo("No verification data provided (use --hash or --signature)", err=True)
            sys.exit(1)
    
    # Check for manifest inside package
    if package_path.suffix == ".zip":
        import zipfile
        import json
        
        try:
            with zipfile.ZipFile(package_path, "r") as zf:
                if "looma.json" in zf.namelist():
                    click.echo("Verifying package manifest...")
                    
                    manifest_data = zf.read("looma.json")
                    manifest = json.loads(manifest_data)
                    
                    # Verify manifest signature if present
                    if "signature" in manifest:
                        verifier = Verifier(config)
                        
                        if verifier.verify_manifest(manifest):
                            click.echo(f"  Manifest verification: PASSED")
                        else:
                            click.echo(f"  Manifest verification: FAILED", err=True)
                            verification_passed = False
                    
                    # Display manifest info
                    if verbose:
                        click.echo("\nManifest Information:")
                        click.echo(f"  App: {manifest.get('app', {}).get('name', 'Unknown')}")
                        click.echo(f"  Version: {manifest.get('app', {}).get('version', 'Unknown')}")
                        click.echo(f"  Build Date: {manifest.get('build_date', 'Unknown')}")
        except Exception as e:
            if verbose:
                click.echo(f"Could not read manifest: {e}", err=True)
    
    # Final result
    if verification_passed:
        click.echo(f"\nPackage verification: PASSED")
        click.echo(f"Package: {package_path}")
        
        # Show package info
        size = package_path.stat().st_size
        click.echo(f"Size: {size:,} bytes")
        
        if verbose:
            # Calculate and show all hashes
            click.echo("\nHashes:")
            for algo in ["sha256", "sha512", "md5"]:
                hash_value = calculate_hash(package_path, algo)
                click.echo(f"  {algo.upper()}: {hash_value}")
    else:
        click.echo(f"\nPackage verification: FAILED", err=True)
        
        if strict or config.get("security", {}).get("verification", {}).get("strict"):
            sys.exit(1)
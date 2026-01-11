"""
Secure credential management for repository connectors.

Provides encrypted storage and retrieval of API tokens and credentials.
"""

from typing import Optional, Dict
from dataclasses import dataclass
import json
import os
from pathlib import Path
from base64 import b64encode, b64decode

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


@dataclass
class RepoCredential:
    """Represents repository credentials."""
    provider: str  # 'github', 'gitlab', 'bitbucket'
    owner: str
    repo: str
    token: str
    url: Optional[str] = None  # For self-hosted instances
    source_branch: Optional[str] = None  # Source branch to migrate from (e.g., 'main', 'develop')
    target_branch: Optional[str] = None  # Target branch for transformations (test mode)


class CredentialManager:
    """
    Secure credential storage using encryption.
    
    Features:
    - Encrypted storage of tokens
    - Per-repository credentials
    - Environment variable fallback
    - No plaintext storage
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize credential manager.
        
        Args:
            config_dir: Directory for storing encrypted credentials
                       (defaults to ~/.crossbridge)
        
        Raises:
            ImportError: If cryptography is not installed
        """
        if not CRYPTO_AVAILABLE:
            raise ImportError(
                "cryptography is required for secure credential storage. "
                "Install with: pip install cryptography"
            )
        
        if config_dir is None:
            config_dir = os.path.expanduser("~/.crossbridge")
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.credentials_file = self.config_dir / "credentials.enc"
        self._cipher = None
        self._credentials: Dict[str, RepoCredential] = {}
    
    def _get_encryption_key(self) -> bytes:
        """
        Get or create encryption key.
        
        Returns:
            Encryption key bytes
        """
        key_file = self.config_dir / ".key"
        
        if key_file.exists():
            return key_file.read_bytes()
        
        # Generate new key
        key = Fernet.generate_key()
        key_file.write_bytes(key)
        key_file.chmod(0o600)  # Read/write for owner only
        
        return key
    
    def _get_cipher(self) -> Fernet:
        """Get Fernet cipher for encryption/decryption."""
        if self._cipher is None:
            key = self._get_encryption_key()
            self._cipher = Fernet(key)
        return self._cipher
    
    def _load_credentials(self):
        """Load encrypted credentials from disk."""
        if not self.credentials_file.exists():
            self._credentials = {}
            return
        
        try:
            encrypted_data = self.credentials_file.read_bytes()
            cipher = self._get_cipher()
            decrypted_data = cipher.decrypt(encrypted_data)
            data = json.loads(decrypted_data.decode('utf-8'))
            
            self._credentials = {
                key: RepoCredential(**cred_data)
                for key, cred_data in data.items()
            }
        except Exception as e:
            # If decryption fails, start with empty credentials
            self._credentials = {}
    
    def _save_credentials(self):
        """Save encrypted credentials to disk."""
        data = {
            key: {
                'provider': cred.provider,
                'owner': cred.owner,
                'repo': cred.repo,
                'token': cred.token,
                'url': cred.url,
                'source_branch': cred.source_branch,
                'target_branch': cred.target_branch
            }
            for key, cred in self._credentials.items()
        }
        
        cipher = self._get_cipher()
        json_data = json.dumps(data).encode('utf-8')
        encrypted_data = cipher.encrypt(json_data)
        
        self.credentials_file.write_bytes(encrypted_data)
        self.credentials_file.chmod(0o600)  # Read/write for owner only
    
    def _make_key(self, provider: str, owner: str, repo: str) -> str:
        """Generate unique key for credential storage."""
        return f"{provider}:{owner}/{repo}"
    
    def store(self, credential: RepoCredential):
        """
        Store repository credential securely.
        
        Args:
            credential: RepoCredential to store
        """
        if not self._credentials:
            self._load_credentials()
        
        key = self._make_key(credential.provider, credential.owner, credential.repo)
        self._credentials[key] = credential
        self._save_credentials()
    
    def get(self, provider: str, owner: str, repo: str) -> Optional[RepoCredential]:
        """
        Retrieve repository credential.
        
        Args:
            provider: Provider name ('github', 'gitlab', etc.)
            owner: Repository owner
            repo: Repository name
            
        Returns:
            RepoCredential or None if not found
        """
        if not self._credentials:
            self._load_credentials()
        
        key = self._make_key(provider, owner, repo)
        return self._credentials.get(key)
    
    def delete(self, provider: str, owner: str, repo: str) -> bool:
        """
        Delete repository credential.
        
        Args:
            provider: Provider name
            owner: Repository owner
            repo: Repository name
            
        Returns:
            True if credential was deleted, False if not found
        """
        if not self._credentials:
            self._load_credentials()
        
        key = self._make_key(provider, owner, repo)
        if key in self._credentials:
            del self._credentials[key]
            self._save_credentials()
            return True
        return False
    
    def list_credentials(self) -> list[tuple[str, str, str]]:
        """
        List all stored credentials (without tokens).
        
        Returns:
            List of (provider, owner, repo) tuples
        """
        if not self._credentials:
            self._load_credentials()
        
        return [
            (cred.provider, cred.owner, cred.repo)
            for cred in self._credentials.values()
        ]
    
    def get_from_env(self, provider: str) -> Optional[str]:
        """
        Get token from environment variable.
        
        Args:
            provider: Provider name
            
        Returns:
            Token from environment or None
        """
        env_vars = {
            'github': 'GITHUB_TOKEN',
            'gitlab': 'GITLAB_TOKEN',
            'bitbucket': 'BITBUCKET_TOKEN'
        }
        
        var_name = env_vars.get(provider.lower())
        if var_name:
            return os.environ.get(var_name)
        
        return None
    
    def get_token(self, provider: str, owner: str, repo: str) -> Optional[str]:
        """
        Get token from stored credentials or environment.
        
        Priority:
        1. Stored credential
        2. Environment variable
        
        Args:
            provider: Provider name
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Token string or None
        """
        # Try stored credential first
        cred = self.get(provider, owner, repo)
        if cred:
            return cred.token
        
        # Fall back to environment variable
        return self.get_from_env(provider)
    
    def clear_all(self):
        """Delete all stored credentials."""
        self._credentials = {}
        if self.credentials_file.exists():
            self.credentials_file.unlink()

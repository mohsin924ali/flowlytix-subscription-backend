"""
Security Module

JWT token management and authentication utilities.
Follows Instructions file standards for security implementation.
"""

import secrets
import structlog
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union

from jose import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from passlib.context import CryptContext

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityException(Exception):
    """Base exception for security-related errors."""
    pass


class TokenException(SecurityException):
    """Exception for token-related errors."""
    pass


class PasswordManager:
    """
    Password hashing and verification manager.
    
    Follows Instructions file standards for security implementation.
    """
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Hashed password string
        """
        if not password:
            raise ValueError("Password cannot be empty")
        
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to verify against
            
        Returns:
            True if password matches, False otherwise
        """
        if not plain_password or not hashed_password:
            return False
        
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.warning("Password verification failed", error=str(e))
            return False


class JWTManager:
    """
    JWT token manager for subscription validation.
    
    Implements RS256 algorithm for enhanced security with public/private key pairs.
    Follows Instructions file standards for security and resource management.
    """
    
    def __init__(self) -> None:
        self._private_key: Optional[Any] = None
        self._public_key: Optional[Any] = None
        self._initialize_keys()
    
    def _initialize_keys(self) -> None:
        """
        Initialize RSA keys for JWT signing and verification.
        
        Creates keys if they don't exist, loads them if they do.
        """
        try:
            private_key_path = Path(settings.private_key_path)
            public_key_path = Path(settings.public_key_path)
            
            # Create keys directory if it doesn't exist
            private_key_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate keys if they don't exist
            if not private_key_path.exists() or not public_key_path.exists():
                logger.info("Generating new RSA key pair for JWT signing")
                self._generate_key_pair(private_key_path, public_key_path)
            
            # Load existing keys
            self._load_keys(private_key_path, public_key_path)
            logger.info("JWT keys initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize JWT keys", error=str(e))
            raise SecurityException(f"Failed to initialize JWT keys: {e}")
    
    def _generate_key_pair(self, private_key_path: Path, public_key_path: Path) -> None:
        """Generate RSA key pair for JWT signing."""
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Generate public key
        public_key = private_key.public_key()
        
        # Serialize and save private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize and save public key
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Write keys to files
        private_key_path.write_bytes(private_pem)
        public_key_path.write_bytes(public_pem)
        
        # Set secure permissions
        private_key_path.chmod(0o600)
        public_key_path.chmod(0o644)
    
    def _load_keys(self, private_key_path: Path, public_key_path: Path) -> None:
        """Load RSA keys from files."""
        # Load private key
        private_key_data = private_key_path.read_bytes()
        self._private_key = serialization.load_pem_private_key(
            private_key_data,
            password=None
        )
        
        # Load public key
        public_key_data = public_key_path.read_bytes()
        self._public_key = serialization.load_pem_public_key(public_key_data)
    
    def generate_subscription_token(self, subscription_data: Dict[str, Any]) -> str:
        """
        Generate a JWT token for subscription validation.
        
        Args:
            subscription_data: Dictionary containing subscription information
            
        Returns:
            JWT token string
            
        Raises:
            TokenException: If token generation fails
        """
        if not self._private_key:
            raise TokenException("Private key not initialized")
        
        try:
            now = datetime.now(timezone.utc)
            expires_at = subscription_data.get('expires_at')
            
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            
            payload = {
                'subscription_id': str(subscription_data['id']),
                'customer_id': str(subscription_data['customer_id']),
                'tier': subscription_data['tier'],
                'features': subscription_data['features'],
                'device_id': subscription_data['device_id'],
                'expires_at': expires_at.isoformat() if expires_at else None,
                'grace_period_days': subscription_data.get('grace_period_days', settings.default_grace_period_days),
                'iss': 'flowlytix-licensing',
                'aud': 'flowlytix-app',
                'iat': int(now.timestamp()),
                'exp': int((now + timedelta(days=30)).timestamp()),  # Token expires in 30 days
                'jti': secrets.token_urlsafe(16),  # Unique token ID
            }
            
            token = jwt.encode(payload, self._private_key, algorithm='RS256')
            
            logger.info(
                "Subscription token generated",
                subscription_id=payload['subscription_id'],
                device_id=payload['device_id']
            )
            
            return token
            
        except Exception as e:
            logger.error("Failed to generate subscription token", error=str(e))
            raise TokenException(f"Failed to generate token: {e}")
    
    def verify_subscription_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode a subscription token.
        
        Args:
            token: JWT token string to verify
            
        Returns:
            Dictionary with verification result and payload
        """
        if not self._public_key:
            raise TokenException("Public key not initialized")
        
        try:
            payload = jwt.decode(
                token,
                self._public_key,
                algorithms=['RS256'],
                audience='flowlytix-app',
                issuer='flowlytix-licensing',
                options={
                    'verify_signature': True,
                    'verify_exp': True,
                    'verify_iat': True,
                    'verify_aud': True,
                    'verify_iss': True,
                }
            )
            
            return {'valid': True, 'payload': payload}
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token verification failed: token expired")
            return {'valid': False, 'error': 'token_expired'}
        except jwt.InvalidTokenError as e:
            logger.warning("Token verification failed: invalid token", error=str(e))
            return {'valid': False, 'error': 'invalid_token'}
        except Exception as e:
            logger.error("Unexpected error during token verification", error=str(e))
            return {'valid': False, 'error': 'verification_error'}
    
    def generate_access_token(self, user_data: Dict[str, Any]) -> str:
        """
        Generate an access token for dashboard authentication.
        
        Args:
            user_data: Dictionary containing user information
            
        Returns:
            JWT access token string
        """
        try:
            now = datetime.now(timezone.utc)
            expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
            
            payload = {
                'sub': str(user_data['id']),
                'email': user_data['email'],
                'role': user_data.get('role', 'user'),
                'iss': 'flowlytix-dashboard',
                'aud': 'flowlytix-dashboard',
                'iat': int(now.timestamp()),
                'exp': int((now + expires_delta).timestamp()),
                'type': 'access',
            }
            
            return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
            
        except Exception as e:
            logger.error("Failed to generate access token", error=str(e))
            raise TokenException(f"Failed to generate access token: {e}")
    
    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode an access token.
        
        Args:
            token: JWT access token string to verify
            
        Returns:
            Dictionary with verification result and payload
        """
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm],
                audience='flowlytix-dashboard',
                issuer='flowlytix-dashboard',
            )
            
            return {'valid': True, 'payload': payload}
            
        except jwt.ExpiredSignatureError:
            return {'valid': False, 'error': 'token_expired'}
        except jwt.InvalidTokenError:
            return {'valid': False, 'error': 'invalid_token'}


class LicenseKeyGenerator:
    """
    License key generator for subscription management.
    
    Follows Instructions file standards for security and uniqueness.
    """
    
    @staticmethod
    def generate_license_key(prefix: str = "FL", length: int = None) -> str:
        """
        Generate a unique license key.
        
        Args:
            prefix: Prefix for the license key
            length: Total length of the key (excluding prefix and separators)
            
        Returns:
            Generated license key
        """
        if length is None:
            length = settings.license_key_length
        
        # Generate random key parts
        key_length = length - len(prefix) - 3  # Account for prefix and separators
        key_parts = []
        
        for _ in range(4):  # Create 4 parts
            part_length = key_length // 4
            part = secrets.token_urlsafe(part_length)[:part_length].upper()
            # Replace URL-safe characters with alphanumeric
            part = part.replace('-', '0').replace('_', '1')
            key_parts.append(part)
        
        return f"{prefix}-{'-'.join(key_parts)}"
    
    @staticmethod
    def validate_license_key_format(license_key: str) -> bool:
        """
        Validate license key format.
        
        Args:
            license_key: License key to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        if not license_key:
            return False
        
        # Basic format validation (FL-XXXX-XXXX-XXXX-XXXX)
        parts = license_key.split('-')
        if len(parts) != 5:
            return False
        
        if parts[0] != 'FL':
            return False
        
        # Check that all parts after prefix are alphanumeric
        for part in parts[1:]:
            if not part.isalnum() or len(part) < 4:
                return False
        
        return True


class SecurityManager:
    """
    Unified security manager providing all security operations.
    
    Acts as a facade for password hashing, JWT operations, and license key generation.
    Follows Instructions file standards for security management.
    """
    
    def __init__(self):
        self.password_manager = PasswordManager()
        self.jwt_manager = JWTManager()
        self.license_key_generator = LicenseKeyGenerator()
    
    # Password management methods
    def hash_password(self, password: str) -> str:
        """Hash a password."""
        return self.password_manager.hash_password(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.password_manager.verify_password(plain_password, hashed_password)
    
    # JWT management methods
    def generate_subscription_token(self, subscription_data: Dict[str, Any]) -> str:
        """Generate a subscription token."""
        return self.jwt_manager.generate_subscription_token(subscription_data)
    
    def verify_subscription_token(self, token: str) -> Dict[str, Any]:
        """Verify a subscription token."""
        return self.jwt_manager.verify_subscription_token(token)
    
    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """Generate an access token."""
        return self.jwt_manager.generate_access_token(user_data)
    
    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """Verify an access token."""
        return self.jwt_manager.verify_access_token(token)
    
    # License key management methods
    def generate_license_key(self, prefix: str = "FL", length: int = None) -> str:
        """Generate a license key."""
        return self.license_key_generator.generate_license_key(prefix, length)
    
    def validate_license_key_format(self, license_key: str) -> bool:
        """Validate license key format."""
        return self.license_key_generator.validate_license_key_format(license_key)


# Global instances
password_manager = PasswordManager()
jwt_manager = JWTManager()
license_key_generator = LicenseKeyGenerator()
security_manager = SecurityManager() 
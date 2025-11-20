"""Authentication and token management for synthetic APIs."""
import secrets
import hashlib
from typing import Dict, Optional
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models import TokenInfo, AuthType


# JWT Configuration
SECRET_KEY = secrets.token_urlsafe(32)
ALGORITHM = "HS256"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token auth
security = HTTPBearer()


class TokenManager:
    """Manages OAuth2 tokens and API keys."""
    
    def __init__(self):
        self.active_tokens: Dict[str, TokenInfo] = {}
        self.api_keys: Dict[str, Dict[str, str]] = {}  # api_key -> {service_id, tenant_id}
        self.token_rotation_counts: Dict[str, int] = {}
        
        # Pre-seed some API keys for testing
        self._seed_api_keys()
    
    def _seed_api_keys(self):
        """Pre-populate some test API keys."""
        test_keys = [
            ("sk_test_mongodb_1234", "mongodb_mock", "tenant1"),
            ("sk_test_stripe_5678", "stripe_mock", "tenant1"),
            ("sk_test_datadog_9012", "datadog_mock", "tenant1"),
        ]
        
        for key, service, tenant in test_keys:
            self.api_keys[key] = {
                "service_id": service,
                "tenant_id": tenant
            }
    
    def create_access_token(
        self,
        service_id: str,
        tenant_id: str,
        expires_delta: timedelta
    ) -> TokenInfo:
        """Create a new OAuth2 access token."""
        expire = datetime.utcnow() + expires_delta
        
        # Create token payload
        payload = {
            "sub": f"{service_id}:{tenant_id}",
            "service_id": service_id,
            "tenant_id": tenant_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "token_id": secrets.token_urlsafe(16)
        }
        
        # Generate token
        access_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
        # Store token info
        token_info = TokenInfo(
            access_token=access_token,
            token_type="Bearer",
            expires_in=int(expires_delta.total_seconds()),
            expires_at=expire,
            refresh_token=secrets.token_urlsafe(32)
        )
        
        self.active_tokens[access_token] = token_info
        
        # Track rotation count
        key = f"{service_id}:{tenant_id}"
        self.token_rotation_counts[key] = self.token_rotation_counts.get(key, 0) + 1
        
        return token_info
    
    def validate_token(self, token: str) -> Dict[str, str]:
        """Validate an OAuth2 token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Check if token is in active list
            if token not in self.active_tokens:
                raise HTTPException(status_code=401, detail="Token revoked")
            
            # Check expiration
            exp = datetime.fromtimestamp(payload["exp"])
            if datetime.utcnow() > exp:
                raise HTTPException(status_code=401, detail="Token expired")
            
            return {
                "service_id": payload["service_id"],
                "tenant_id": payload["tenant_id"]
            }
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def validate_api_key(self, api_key: str) -> Dict[str, str]:
        """Validate an API key."""
        if api_key not in self.api_keys:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        return self.api_keys[api_key]
    
    def revoke_token(self, token: str):
        """Revoke an access token."""
        if token in self.active_tokens:
            del self.active_tokens[token]
    
    def should_rotate_token(self, service_id: str, call_count: int, rotate_every: Optional[int]) -> bool:
        """Check if token should be rotated based on call count."""
        if rotate_every and call_count > 0 and call_count % rotate_every == 0:
            return True
        return False
    
    def get_token_metrics(self) -> Dict[str, Any]:
        """Get token management metrics."""
        return {
            "active_tokens": len(self.active_tokens),
            "api_keys": len(self.api_keys),
            "token_rotations": dict(self.token_rotation_counts),
            "expired_tokens": sum(
                1 for token in self.active_tokens.values()
                if datetime.utcnow() > token.expires_at
            )
        }


class AuthValidator:
    """Validates authentication based on service configuration."""
    
    def __init__(self, token_manager: TokenManager):
        self.token_manager = token_manager
    
    def validate_request(
        self,
        auth_type: AuthType,
        credentials: Optional[HTTPAuthorizationCredentials],
        service_id: str
    ) -> Dict[str, str]:
        """Validate authentication credentials."""
        if auth_type == AuthType.NONE:
            return {"service_id": service_id, "tenant_id": "default"}
        
        if not credentials:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        if auth_type == AuthType.OAUTH2_CLIENT_CREDENTIALS:
            # Validate OAuth2 Bearer token
            return self.token_manager.validate_token(credentials.credentials)
        
        elif auth_type == AuthType.API_KEY:
            # API key should be in Authorization header as Bearer
            return self.token_manager.validate_api_key(credentials.credentials)
        
        elif auth_type == AuthType.BASIC_AUTH:
            # For basic auth, we'll just check if credentials exist
            # In a real system, we'd validate username/password
            return {"service_id": service_id, "tenant_id": "default"}
        
        raise HTTPException(status_code=401, detail="Unsupported authentication type")
"""
Salesforce OAuth Token Refresh
Handles OAuth 2.0 refresh token flow for Salesforce
"""
import httpx
from datetime import datetime, timedelta
from typing import Dict, Optional


class TokenCache:
    """Simple in-memory token cache with expiry"""
    
    def __init__(self):
        self.access_token: Optional[str] = None
        self.expires_at: Optional[datetime] = None
    
    def is_valid(self) -> bool:
        """Check if cached token is still valid"""
        if not self.access_token or not self.expires_at:
            return False
        return datetime.utcnow() < self.expires_at
    
    def set(self, access_token: str, expires_in: int = 3300):
        """Cache token with expiry time"""
        self.access_token = access_token
        self.expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)
    
    def get(self) -> Optional[str]:
        """Get cached token if still valid"""
        if self.is_valid():
            return self.access_token
        return None


_token_cache = TokenCache()


def refresh_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    instance_url: str = "https://login.salesforce.com"
) -> Dict[str, str]:
    """
    Refresh Salesforce OAuth access token
    
    Args:
        client_id: Salesforce Connected App Client ID
        client_secret: Salesforce Connected App Client Secret
        refresh_token: Salesforce refresh token
        instance_url: Salesforce instance URL (default: login.salesforce.com)
    
    Returns:
        Dictionary with:
        - access_token: New access token
        - instance_url: Salesforce instance URL
        - token_type: Bearer
        - expires_in: 3300 (seconds)
    
    Raises:
        Exception: If refresh fails
    """
    # Check cache first
    cached_token = _token_cache.get()
    if cached_token:
        return {
            "access_token": cached_token,
            "instance_url": instance_url,
            "token_type": "Bearer",
            "expires_in": 3300
        }
    
    # OAuth token endpoint
    token_url = f"{instance_url}/services/oauth2/token"
    
    # Prepare refresh token request
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token
    }
    
    try:
        response = httpx.post(token_url, data=data, timeout=30.0)
        response.raise_for_status()
        
        token_data = response.json()
        
        # Extract access token
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError("No access_token in response")
        
        # Cache the token
        _token_cache.set(access_token, expires_in=3300)
        
        return {
            "access_token": access_token,
            "instance_url": token_data.get("instance_url", instance_url),
            "token_type": token_data.get("token_type", "Bearer"),
            "expires_in": 3300
        }
    
    except httpx.HTTPStatusError as e:
        raise Exception(f"Salesforce OAuth refresh failed: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise Exception(f"Salesforce OAuth refresh error: {e}")


def get_access_token(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    refresh_token: Optional[str] = None,
    direct_access_token: Optional[str] = None
) -> Optional[str]:
    """
    Get access token - either from direct token or via refresh flow
    
    Args:
        client_id: Salesforce Client ID (for refresh flow)
        client_secret: Salesforce Client Secret (for refresh flow)
        refresh_token: Salesforce refresh token (for refresh flow)
        direct_access_token: Direct access token (if available)
    
    Returns:
        Access token or None if both methods unavailable
    """
    # If direct access token provided, use it
    if direct_access_token:
        return direct_access_token
    
    # Otherwise, use refresh flow
    if client_id and client_secret and refresh_token:
        try:
            token_data = refresh_access_token(client_id, client_secret, refresh_token)
            return token_data.get("access_token")
        except Exception:
            return None
    
    return None

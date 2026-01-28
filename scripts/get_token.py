#!/usr/bin/env python3
"""
Get or create test user and generate JWT token for testing
"""

import sys
import requests
import os


def get_auth_token(api_url: str = "http://localhost:5000") -> str:
    """Register test user and get JWT token"""
    
    # Try to register (may fail if user exists)
    register_data = {
        "name": "AAM Test Org",
        "email": "aam-test@autonomos.dev",
        "password": "test123!Safe"
    }
    
    try:
        response = requests.post(f"{api_url}/api/v1/auth/register", json=register_data)
        if response.status_code == 200:
            print("✅ Test user registered successfully")
    except Exception:
        pass  # User may already exist, or network error - continue to login
    
    # Login to get token
    login_data = {
        "email": "aam-test@autonomos.dev",
        "password": "test123!Safe"
    }
    
    response = requests.post(f"{api_url}/api/v1/auth/login", json=login_data)
    
    if response.status_code == 200:
        data = response.json()
        token = data.get('access_token')
        print("✅ JWT token generated successfully")
        print()
        print("Export this token:")
        print(f"export AAM_AUTH_TOKEN={token}")
        return token
    else:
        print(f"❌ Login failed: {response.status_code} {response.text}")
        sys.exit(1)


if __name__ == '__main__':
    api_url = os.getenv('AAM_API_URL', 'http://localhost:5000')
    get_auth_token(api_url)

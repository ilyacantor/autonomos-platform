#!/usr/bin/env python3
"""
Register real AAM connections using environment secrets
Creates functional connection records that reference actual credentials
"""
import os
import sys
import requests
from datetime import datetime

# API base URL
API_BASE = "http://localhost:5000/api/v1"

# Test user credentials
TEST_USER = "aostest@autonomos.dev"
TEST_PASS = "TestPass123!"


def get_auth_token():
    """Login and get JWT token"""
    response = requests.post(
        f"{API_BASE}/auth/login",
        json={"email": TEST_USER, "password": TEST_PASS}
    )
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None
    
    token = response.json().get("access_token")
    print(f"✅ Authenticated as {TEST_USER}")
    return token


def register_salesforce(token):
    """Register Salesforce connection"""
    access_token = os.getenv("SALESFORCE_ACCESS_TOKEN")
    instance_url = os.getenv("SALESFORCE_INSTANCE_URL")
    
    if not access_token or not instance_url:
        print("⚠️  Salesforce credentials not found - skipping")
        return None
    
    config = {
        "name": "Salesforce Production",
        "source_type": "salesforce",
        "connector_config": {
            "instance_url": instance_url,
            "access_token": access_token
        }
    }
    
    response = requests.post(
        f"{API_BASE}/aam/connections",
        json=config,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 201:
        conn = response.json()
        print(f"✅ Salesforce connection created: {conn['id']}")
        return conn
    else:
        print(f"❌ Salesforce connection failed: {response.status_code}")
        print(response.text)
        return None


def register_mongodb(token):
    """Register MongoDB connection"""
    mongodb_uri = os.getenv("MONGODB_URI")
    
    if not mongodb_uri:
        print("⚠️  MongoDB URI not found - skipping")
        return None
    
    # Extract database name from URI (default to 'autonomos')
    database = "autonomos"  # Adjust if needed
    
    config = {
        "name": "MongoDB Production",
        "source_type": "mongodb",
        "connector_config": {
            "connection_string": mongodb_uri,
            "database": database
        }
    }
    
    response = requests.post(
        f"{API_BASE}/aam/connections",
        json=config,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 201:
        conn = response.json()
        print(f"✅ MongoDB connection created: {conn['id']}")
        return conn
    else:
        print(f"❌ MongoDB connection failed: {response.status_code}")
        print(response.text)
        return None


def register_supabase(token):
    """Register Supabase connection"""
    supabase_url = os.getenv("SUPABASE_DB_URL")
    
    if not supabase_url:
        print("⚠️  Supabase URL not found - skipping")
        return None
    
    config = {
        "name": "Supabase Production",
        "source_type": "supabase",
        "connector_config": {
            "connection_string": supabase_url,
            "schema": "public"  # Adjust if needed
        }
    }
    
    response = requests.post(
        f"{API_BASE}/aam/connections",
        json=config,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 201:
        conn = response.json()
        print(f"✅ Supabase connection created: {conn['id']}")
        return conn
    else:
        print(f"❌ Supabase connection failed: {response.status_code}")
        print(response.text)
        return None


def main():
    print("=" * 60)
    print("Register Real AAM Connections")
    print("=" * 60)
    
    # Login
    token = get_auth_token()
    if not token:
        sys.exit(1)
    
    print("\n📝 Registering connections using environment secrets...\n")
    
    # Register each connection
    salesforce_conn = register_salesforce(token)
    mongodb_conn = register_mongodb(token)
    supabase_conn = register_supabase(token)
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    connections_created = sum([
        1 if salesforce_conn else 0,
        1 if mongodb_conn else 0,
        1 if supabase_conn else 0
    ])
    print(f"✅ {connections_created} real connections registered")
    print("=" * 60)
    
    return 0 if connections_created > 0 else 1


if __name__ == "__main__":
    sys.exit(main())

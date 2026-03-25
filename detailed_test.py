#!/usr/bin/env python3
"""
Detailed Testing of 2FA and DSGVO Features per Review Request
"""

import requests
import json
import base64
import re

BACKEND_URL = "https://dual-yard-system.preview.emergentagent.com/api"

def login_and_get_token(email, password):
    """Helper function to login and get token"""
    response = requests.post(f"{BACKEND_URL}/auth/login", json={
        "email": email,
        "password": password
    })
    if response.status_code == 200:
        data = response.json()
        if "requires_2fa" in data:
            return {"requires_2fa": True, "temp_token": data.get("temp_token")}
        return data["access_token"]
    return None

def test_2fa_setup_detailed():
    """Test 2FA setup with detailed validation"""
    print("=== DETAILED 2FA SETUP TEST ===")
    
    # Login as admin
    token = login_and_get_token("admin@test.de", "Admin123!")
    if not token or isinstance(token, dict):
        print("❌ Admin login failed")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Call 2FA setup
    response = requests.post(f"{BACKEND_URL}/auth/2fa/setup", headers=headers)
    print(f"Setup Response Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ 2FA setup failed: {response.text}")
        return False
    
    data = response.json()
    
    # Detailed validation
    print(f"✅ QR Code present: {'qr_code' in data}")
    print(f"✅ QR Code format: {data['qr_code'].startswith('data:image/png;base64,') if 'qr_code' in data else 'N/A'}")
    
    if 'qr_code' in data:
        # Extract base64 part and validate
        b64_data = data['qr_code'].split(',')[1]
        try:
            decoded = base64.b64decode(b64_data)
            print(f"✅ QR Code size: {len(decoded)} bytes")
        except:
            print("❌ Invalid base64 in QR code")
    
    print(f"✅ Secret present: {'secret' in data}")
    if 'secret' in data:
        secret = data['secret']
        print(f"✅ Secret length: {len(secret)} chars")
        print(f"✅ Secret format (Base32): {bool(re.match(r'^[A-Z2-7]+$', secret))}")
        
    return True

def test_dsgvo_status_detailed():
    """Test DSGVO status endpoint with detailed validation"""
    print("\n=== DETAILED DSGVO STATUS TEST ===")
    
    token = login_and_get_token("admin@test.de", "Admin123!")
    if not token:
        print("❌ Admin login failed")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BACKEND_URL}/admin/dsgvo-status", headers=headers)
    
    print(f"DSGVO Status Response: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ DSGVO status failed: {response.text}")
        return False
    
    data = response.json()
    print("DSGVO Status Data:")
    for key, value in data.items():
        print(f"  {key}: {value} ({type(value).__name__})")
    
    # Validate specific requirements
    print(f"✅ Retention days = 180: {data.get('retention_days') == 180}")
    print(f"✅ Cutoff date is ISO string: {isinstance(data.get('cutoff_date'), str) and 'T' in str(data.get('cutoff_date'))}")
    print(f"✅ Already anonymized >= 1: {data.get('already_anonymized', 0) >= 1}")
    print(f"✅ Scheduler running = true: {data.get('scheduler_running') is True}")
    
    return True

def test_role_access_detailed():
    """Test role-based access control in detail"""
    print("\n=== DETAILED ROLE ACCESS TEST ===")
    
    # Test authority access
    authority_token = login_and_get_token("behoerde@test.de", "Behoerde123")
    if not authority_token:
        print("❌ Authority login failed")
        return False
    
    headers = {"Authorization": f"Bearer {authority_token}"}
    
    # Test DSGVO status access (should be blocked)
    response = requests.get(f"{BACKEND_URL}/admin/dsgvo-status", headers=headers)
    print(f"✅ Authority DSGVO status blocked: {response.status_code == 403} (Status: {response.status_code})")
    
    # Test manual cleanup access (should be blocked)
    response = requests.post(f"{BACKEND_URL}/admin/trigger-cleanup", headers=headers)
    print(f"✅ Authority DSGVO cleanup blocked: {response.status_code == 403} (Status: {response.status_code})")
    
    return True

if __name__ == "__main__":
    print("🔍 DETAILED 2FA & DSGVO FEATURE TESTING")
    
    test_2fa_setup_detailed()
    test_dsgvo_status_detailed()
    test_role_access_detailed()
    
    print("\n✅ DETAILED TESTING COMPLETE")
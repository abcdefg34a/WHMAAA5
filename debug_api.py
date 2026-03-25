#!/usr/bin/env python3
"""
Debug script to check the failing API responses
"""

import requests
import json
import os

# Get backend URL from environment
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://dual-yard-system.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

# Test credentials
AUTHORITY_CREDENTIALS = {
    "email": "behoerde@test.de", 
    "password": "Behoerde123!"
}

TOWING_SERVICE_CREDENTIALS = {
    "email": "abschlepp@test.de",
    "password": "Abschlepp123!"
}

def login_and_debug():
    # Login as authority
    print("=== Authority Login ===")
    response = requests.post(f"{API_BASE}/auth/login", json=AUTHORITY_CREDENTIALS)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        auth_data = response.json()
        authority_token = auth_data["access_token"]
        print("Authority login successful")
        
        # Test calculate costs with a job ID
        print("\n=== Testing Calculate Costs ===")
        job_id = "45b92eee-70e8-4cc7-861a-65729224aefa"  # From previous test
        headers = {"Authorization": f"Bearer {authority_token}"}
        response = requests.get(f"{API_BASE}/jobs/{job_id}/calculate-costs", headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
    # Login as towing service
    print("\n=== Towing Service Login ===")
    response = requests.post(f"{API_BASE}/auth/login", json=TOWING_SERVICE_CREDENTIALS)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        towing_data = response.json()
        towing_token = towing_data["access_token"]
        print("Towing service login successful")
        
        # Test get invoices
        print("\n=== Testing Get Invoices ===")
        headers = {"Authorization": f"Bearer {towing_token}"}
        response = requests.get(f"{API_BASE}/services/invoices", headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    login_and_debug()
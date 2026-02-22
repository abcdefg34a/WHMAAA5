#!/usr/bin/env python3

import requests
import json

# Debug user object for employee
base_url = "https://impound-pro.preview.emergentagent.com/api"

# Use existing employee token from previous test
employee_login = {"email": "test_employee_check@test.de", "password": "TestPass123!"}
response = requests.post(f"{base_url}/auth/login", json=employee_login)

if response.status_code == 200:
    employee_token = response.json()['access_token']
    
    # Get user info
    response = requests.get(f"{base_url}/auth/me", 
                          headers={'Authorization': f'Bearer {employee_token}'})
    
    if response.status_code == 200:
        user_data = response.json()
        print("Employee user data:")
        print(json.dumps(user_data, indent=2))
        
        print(f"\nis_main_authority: {user_data.get('is_main_authority')}")
        print(f"parent_authority_id: {user_data.get('parent_authority_id')}")
        print(f"user id: {user_data.get('id')}")
    else:
        print(f"Failed to get user info: {response.status_code}")
else:
    print(f"Failed to login: {response.status_code}")
#!/usr/bin/env python3

import requests
import json

# Test authority_id field in jobs
base_url = "https://dual-yard-system.preview.emergentagent.com/api"

# Register a new authority for testing
authority_data = {
    "email": "test_authority_check@test.de",
    "password": "TestPass123!",
    "name": "Test Authority Check",
    "role": "authority",
    "authority_name": "Test Authority Check",
    "department": "Test Department"
}

print("🔍 Testing authority_id field in jobs...")

# Register authority
response = requests.post(f"{base_url}/auth/register", json=authority_data)
if response.status_code == 200:
    auth_data = response.json()
    authority_token = auth_data['access_token']
    authority_id = auth_data['user']['id']
    print(f"✅ Authority registered - ID: {authority_id}")
    
    # Create employee
    employee_data = {
        "email": "test_employee_check@test.de",
        "password": "TestPass123!",
        "name": "Test Employee Check"
    }
    
    response = requests.post(f"{base_url}/authority/employees", 
                           json=employee_data, 
                           headers={'Authorization': f'Bearer {authority_token}'})
    
    if response.status_code == 200:
        employee_data = response.json()
        employee_id = employee_data['id']
        print(f"✅ Employee created - ID: {employee_id}")
        
        # Login as employee
        login_data = {"email": "test_employee_check@test.de", "password": "TestPass123!"}
        response = requests.post(f"{base_url}/auth/login", json=login_data)
        
        if response.status_code == 200:
            employee_token = response.json()['access_token']
            print(f"✅ Employee logged in")
            
            # Create job as employee
            job_data = {
                "license_plate": "B-CHECK123",
                "tow_reason": "Authority ID check",
                "location_address": "Test Street 1",
                "location_lat": 52.520008,
                "location_lng": 13.404954,
                "notes": "Testing authority_id field"
            }
            
            response = requests.post(f"{base_url}/jobs", 
                                   json=job_data,
                                   headers={'Authorization': f'Bearer {employee_token}'})
            
            if response.status_code == 200:
                job_data = response.json()
                job_authority_id = job_data.get('authority_id')
                created_by_dienstnummer = job_data.get('created_by_dienstnummer')
                
                print(f"✅ Job created by employee")
                print(f"   Job authority_id: {job_authority_id}")
                print(f"   Expected authority_id: {authority_id}")
                print(f"   Created by dienstnummer: {created_by_dienstnummer}")
                
                if job_authority_id == authority_id:
                    print("✅ Authority ID correctly set!")
                else:
                    print("❌ Authority ID not set correctly!")
                    
                # Test main authority can see the job
                response = requests.get(f"{base_url}/jobs", 
                                      headers={'Authorization': f'Bearer {authority_token}'})
                
                if response.status_code == 200:
                    jobs = response.json()
                    employee_jobs = [j for j in jobs if j.get('created_by_dienstnummer') == created_by_dienstnummer]
                    print(f"✅ Main authority sees {len(employee_jobs)} employee jobs")
                else:
                    print(f"❌ Failed to get jobs as main authority: {response.status_code}")
            else:
                print(f"❌ Failed to create job as employee: {response.status_code}")
        else:
            print(f"❌ Failed to login as employee: {response.status_code}")
    else:
        print(f"❌ Failed to create employee: {response.status_code}")
else:
    print(f"❌ Failed to register authority: {response.status_code}")
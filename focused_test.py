#!/usr/bin/env python3

import requests
import json
from datetime import datetime

# Quick focused test of employee management system
base_url = "https://pg-abschlepp-core.preview.emergentagent.com/api"

def test_employee_system():
    print("🏢 Testing Employee Management System - Focused Test")
    
    # Register new authority
    authority_data = {
        "email": f"focused_authority_{datetime.now().strftime('%H%M%S')}@test.de",
        "password": "TestPass123!",
        "name": "Focused Test Authority",
        "role": "authority",
        "authority_name": "Focused Test Authority",
        "department": "Test Department"
    }
    
    response = requests.post(f"{base_url}/auth/register", json=authority_data)
    if response.status_code != 200:
        print(f"❌ Failed to register authority: {response.status_code}")
        return False
    
    auth_data = response.json()
    authority_token = auth_data['access_token']
    authority_id = auth_data['user']['id']
    main_dienstnummer = auth_data['user']['dienstnummer']
    
    print(f"✅ Authority registered - ID: {authority_id}, Dienstnummer: {main_dienstnummer}")
    
    # Create employee
    employee_data = {
        "email": f"focused_employee_{datetime.now().strftime('%H%M%S')}@test.de",
        "password": "TestPass123!",
        "name": "Focused Test Employee"
    }
    
    response = requests.post(f"{base_url}/authority/employees", 
                           json=employee_data, 
                           headers={'Authorization': f'Bearer {authority_token}'})
    
    if response.status_code != 200:
        print(f"❌ Failed to create employee: {response.status_code}")
        return False
    
    emp_data = response.json()
    employee_id = emp_data['id']
    employee_dienstnummer = emp_data['dienstnummer']
    
    print(f"✅ Employee created - ID: {employee_id}, Dienstnummer: {employee_dienstnummer}")
    
    # Login as employee
    login_data = {"email": employee_data["email"], "password": employee_data["password"]}
    response = requests.post(f"{base_url}/auth/login", json=login_data)
    
    if response.status_code != 200:
        print(f"❌ Failed to login as employee: {response.status_code}")
        return False
    
    employee_token = response.json()['access_token']
    print(f"✅ Employee logged in")
    
    # Employee creates job
    job_data = {
        "license_plate": "B-FOCUS123",
        "tow_reason": "Focused test job",
        "location_address": "Focus Street 1",
        "location_lat": 52.520008,
        "location_lng": 13.404954,
        "notes": "Job created by employee for focused test"
    }
    
    response = requests.post(f"{base_url}/jobs", 
                           json=job_data,
                           headers={'Authorization': f'Bearer {employee_token}'})
    
    if response.status_code != 200:
        print(f"❌ Failed to create job as employee: {response.status_code}")
        return False
    
    job_response = response.json()
    job_id = job_response['id']
    job_authority_id = job_response.get('authority_id')
    job_dienstnummer = job_response.get('created_by_dienstnummer')
    
    print(f"✅ Employee job created - ID: {job_id}")
    print(f"   Authority ID: {job_authority_id}")
    print(f"   Created by Dienstnummer: {job_dienstnummer}")
    
    # Verify authority_id is correct
    if job_authority_id == authority_id:
        print("✅ Job authority_id correctly set to main authority")
    else:
        print(f"❌ Job authority_id incorrect - Expected: {authority_id}, Got: {job_authority_id}")
    
    # Verify dienstnummer is correct
    if job_dienstnummer == employee_dienstnummer:
        print("✅ Job dienstnummer correctly set to employee")
    else:
        print(f"❌ Job dienstnummer incorrect - Expected: {employee_dienstnummer}, Got: {job_dienstnummer}")
    
    # Main authority gets jobs (should see employee job)
    response = requests.get(f"{base_url}/jobs", 
                          headers={'Authorization': f'Bearer {authority_token}'})
    
    if response.status_code != 200:
        print(f"❌ Failed to get jobs as main authority: {response.status_code}")
        return False
    
    authority_jobs = response.json()
    employee_jobs = [j for j in authority_jobs if j.get('created_by_dienstnummer') == employee_dienstnummer]
    
    print(f"✅ Main authority sees {len(authority_jobs)} total jobs")
    print(f"   Employee jobs visible: {len(employee_jobs)}")
    
    if len(employee_jobs) >= 1:
        print("✅ Main authority can see employee jobs")
    else:
        print("❌ Main authority cannot see employee jobs")
    
    # Employee gets jobs (should only see own)
    response = requests.get(f"{base_url}/jobs", 
                          headers={'Authorization': f'Bearer {employee_token}'})
    
    if response.status_code != 200:
        print(f"❌ Failed to get jobs as employee: {response.status_code}")
        return False
    
    employee_own_jobs = response.json()
    other_jobs = [j for j in employee_own_jobs if j.get('created_by_dienstnummer') != employee_dienstnummer]
    
    print(f"✅ Employee sees {len(employee_own_jobs)} total jobs")
    print(f"   Other jobs visible: {len(other_jobs)}")
    
    if len(other_jobs) == 0:
        print("✅ Employee correctly sees only own jobs")
    else:
        print("❌ Employee sees jobs they shouldn't see")
    
    return True

if __name__ == "__main__":
    test_employee_system()
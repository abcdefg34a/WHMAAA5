#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AbschleppPortal Backend Comprehensive Test
=========================================

Tests all major endpoints for the AbschleppPortal (Towing Management System):

1. Authentication Tests:
   - POST /api/auth/login (admin@test.de / Admin123!)
   - POST /api/auth/login (behoerde@test.de / Behoerde123!)
   - POST /api/auth/login (abschlepp@test.de / Abschlepp123!)
   - POST /api/auth/forgot-password
   - POST /api/auth/register (new test registration)

2. Jobs API Tests (as Authority behoerde@test.de):
   - GET /api/jobs (list all jobs)
   - GET /api/jobs/count/total
   - POST /api/jobs (create new job)
   - GET /api/jobs/{id}
   - PUT /api/jobs/{id} (update status)

3. Admin Endpoint Tests (as admin@test.de):
   - GET /api/admin/users
   - GET /api/admin/audit-logs
   - POST /api/admin/backup (create database backup)
   - GET /api/admin/backups (list all backups)
   - POST /api/admin/backups/send-test-email
   - POST /api/admin/backups/send-weekly-report
   - GET /api/admin/backups/status

4. Services API Tests:
   - GET /api/services (as Authority)
   - GET /api/towing-services (as Admin)

5. File Upload Test:
   - Test photo upload functionality
"""

import requests
import json
import sys
import time
import base64
from datetime import datetime
from typing import Dict, Optional

# Backend URL from frontend .env
BACKEND_URL = "https://react-state-sync.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "admin@test.de"
ADMIN_PASSWORD = "Admin123!"
AUTHORITY_EMAIL = "behoerde@test.de"
AUTHORITY_PASSWORD = "Behoerde123!"
TOWING_EMAIL = "abschlepp@test.de"
TOWING_PASSWORD = "Abschlepp123!"

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_test(test_name):
    print(f"\n🧪 TEST: {test_name}")

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def print_info(message):
    print(f"ℹ️  {message}")

def make_request(method, endpoint, headers=None, json_data=None, data=None, files=None):
    """Helper function to make HTTP requests with error handling"""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=json_data,
            data=data,
            files=files,
            timeout=60
        )
        return response
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return None

def login_user(email: str, password: str, role_name: str) -> Optional[str]:
    """Login and return token"""
    print_test(f"{role_name} Login")
    
    response = make_request("POST", "/auth/login", json_data={
        "email": email,
        "password": password
    })
    
    if not response:
        print_error("Login request failed")
        return None
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        user = data.get("user", {})
        
        print_success(f"{role_name} login successful")
        print_info(f"Token: {token[:20] if token else 'None'}...")
        print_info(f"User: {user.get('name')} ({user.get('role')})")
        
        return token
    else:
        print_error(f"Login failed: {response.status_code} - {response.text}")
        return None

def test_authentication():
    """Test all authentication endpoints"""
    print_header("AUTHENTICATION TESTS")
    results = {}
    
    # 1. Admin Login
    admin_token = login_user(ADMIN_EMAIL, ADMIN_PASSWORD, "Admin")
    results["admin_login"] = admin_token is not None
    
    # 2. Authority Login
    authority_token = login_user(AUTHORITY_EMAIL, AUTHORITY_PASSWORD, "Authority") 
    results["authority_login"] = authority_token is not None
    
    # 3. Towing Service Login
    towing_token = login_user(TOWING_EMAIL, TOWING_PASSWORD, "Towing Service")
    results["towing_login"] = towing_token is not None
    
    # 4. Password Reset Request
    print_test("Password Reset Request")
    response = make_request("POST", "/auth/forgot-password", json_data={
        "email": "test@example.com"
    })
    
    if response and response.status_code == 200:
        print_success("Password reset request successful")
        results["password_reset"] = True
    else:
        print_error(f"Password reset failed: {response.status_code if response else 'No response'}")
        results["password_reset"] = False
    
    # 5. Test Registration (new user)
    print_test("New User Registration")
    test_email = f"test_{int(time.time())}@example.com"
    response = make_request("POST", "/auth/register", json_data={
        "email": test_email,
        "password": "TestPass123!",
        "role": "authority",
        "name": "Test Authority",
        "authority_name": "Test Department",
        "department": "Traffic Police"
    })
    
    if response and (response.status_code == 202 or response.status_code == 200):
        print_success("Registration successful (waiting for approval)")
        results["registration"] = True
    else:
        print_error(f"Registration failed: {response.status_code if response else 'No response'} - {response.text if response else 'No response'}")
        results["registration"] = False
    
    return results, {
        "admin": admin_token,
        "authority": authority_token, 
        "towing": towing_token
    }

def test_jobs_api(authority_token: str):
    """Test Jobs API endpoints as Authority user"""
    print_header("JOBS API TESTS (as Authority)")
    results = {}
    headers = {"Authorization": f"Bearer {authority_token}"}
    
    # 1. Get all jobs
    print_test("Get All Jobs")
    response = make_request("GET", "/jobs", headers=headers)
    
    if response and response.status_code == 200:
        jobs = response.json()
        print_success(f"Retrieved {len(jobs)} jobs")
        results["get_jobs"] = True
    else:
        print_error(f"Get jobs failed: {response.status_code if response else 'No response'}")
        results["get_jobs"] = False
        jobs = []
    
    # 2. Get job count
    print_test("Get Job Count")
    response = make_request("GET", "/jobs/count/total", headers=headers)
    
    if response and response.status_code == 200:
        count_data = response.json()
        print_success(f"Total jobs count: {count_data}")
        results["job_count"] = True
    else:
        print_error(f"Job count failed: {response.status_code if response else 'No response'}")
        results["job_count"] = False
    
    # 3. Create new job
    print_test("Create New Job")
    job_data = {
        "license_plate": f"TEST-{int(time.time())}",
        "tow_reason": "Falschparken",
        "location_address": "Musterstraße 123, Berlin",
        "location_lat": 52.5200,
        "location_lng": 13.4050,
        "notes": "Test job created by automated test",
        "job_type": "towing"
    }
    
    response = make_request("POST", "/jobs", headers=headers, json_data=job_data)
    
    if response and response.status_code in [200, 201]:
        job = response.json()
        job_id = job.get("id")
        print_success(f"Job created successfully: {job.get('job_number')} (ID: {job_id})")
        results["create_job"] = True
        
        # 4. Get specific job
        if job_id:
            print_test(f"Get Specific Job (ID: {job_id})")
            response = make_request("GET", f"/jobs/{job_id}", headers=headers)
            
            if response and response.status_code == 200:
                job_detail = response.json()
                print_success(f"Retrieved job details: {job_detail.get('job_number')}")
                results["get_job_detail"] = True
            else:
                print_error(f"Get job detail failed: {response.status_code if response else 'No response'}")
                results["get_job_detail"] = False
            
            # 5. Update job status
            print_test(f"Update Job Status (ID: {job_id})")
            update_data = {
                "status": "assigned",
                "notes": "Job status updated by test"
            }
            
            response = make_request("PUT", f"/jobs/{job_id}", headers=headers, json_data=update_data)
            
            if response and response.status_code == 200:
                updated_job = response.json()
                print_success(f"Job status updated: {updated_job.get('status')}")
                results["update_job"] = True
            else:
                print_error(f"Update job failed: {response.status_code if response else 'No response'}")
                results["update_job"] = False
        else:
            results["get_job_detail"] = False
            results["update_job"] = False
    else:
        print_error(f"Create job failed: {response.status_code if response else 'No response'} - {response.text if response else ''}")
        results["create_job"] = False
        results["get_job_detail"] = False
        results["update_job"] = False
    
    return results

def test_admin_endpoints(admin_token: str):
    """Test Admin endpoints"""
    print_header("ADMIN ENDPOINTS TESTS")
    results = {}
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 1. Get all users
    print_test("Get All Users")
    response = make_request("GET", "/admin/users", headers=headers)
    
    if response and response.status_code == 200:
        users = response.json()
        print_success(f"Retrieved {len(users)} users")
        results["get_users"] = True
    else:
        print_error(f"Get users failed: {response.status_code if response else 'No response'}")
        results["get_users"] = False
    
    # 2. Get audit logs
    print_test("Get Audit Logs")
    response = make_request("GET", "/admin/audit-logs", headers=headers)
    
    if response and response.status_code == 200:
        logs = response.json()
        print_success(f"Retrieved {len(logs)} audit logs")
        results["get_audit_logs"] = True
    else:
        print_error(f"Get audit logs failed: {response.status_code if response else 'No response'}")
        results["get_audit_logs"] = False
    
    # 3. Create database backup
    print_test("Create Database Backup")
    response = make_request("POST", "/admin/backup", headers=headers)
    
    if response and response.status_code == 200:
        backup = response.json()
        print_success(f"Database backup created: {backup.get('id')}")
        results["create_backup"] = True
    else:
        print_error(f"Create backup failed: {response.status_code if response else 'No response'}")
        results["create_backup"] = False
    
    # 4. List all backups
    print_test("List All Backups")
    response = make_request("GET", "/admin/backups", headers=headers)
    
    if response and response.status_code == 200:
        backups = response.json()
        backup_list = backups if isinstance(backups, list) else backups.get('backups', [])
        print_success(f"Retrieved {len(backup_list)} backups")
        results["list_backups"] = True
    else:
        print_error(f"List backups failed: {response.status_code if response else 'No response'}")
        results["list_backups"] = False
    
    # 5. Send test email
    print_test("Send Test Email")
    response = make_request("POST", "/admin/backups/send-test-email", headers=headers)
    
    if response and response.status_code == 200:
        email_result = response.json()
        print_success(f"Test email sent: {email_result}")
        results["send_test_email"] = True
    else:
        print_error(f"Send test email failed: {response.status_code if response else 'No response'}")
        results["send_test_email"] = False
    
    # 6. Send weekly report
    print_test("Send Weekly Report")
    response = make_request("POST", "/admin/backups/send-weekly-report", headers=headers)
    
    if response and response.status_code == 200:
        report_result = response.json()
        print_success(f"Weekly report sent: {report_result}")
        results["send_weekly_report"] = True
    else:
        print_error(f"Send weekly report failed: {response.status_code if response else 'No response'}")
        results["send_weekly_report"] = False
    
    # 7. Get backup status
    print_test("Get Backup Status")
    response = make_request("GET", "/admin/backups/status", headers=headers)
    
    if response and response.status_code == 200:
        status = response.json()
        print_success(f"Backup status retrieved: {status}")
        results["backup_status"] = True
    else:
        print_error(f"Get backup status failed: {response.status_code if response else 'No response'}")
        results["backup_status"] = False
    
    return results

def test_services_api(authority_token: str, admin_token: str):
    """Test Services API endpoints"""
    print_header("SERVICES API TESTS")
    results = {}
    
    # 1. Get services (as Authority)
    print_test("Get Services (as Authority)")
    headers = {"Authorization": f"Bearer {authority_token}"}
    response = make_request("GET", "/services", headers=headers)
    
    if response and response.status_code == 200:
        services = response.json()
        print_success(f"Retrieved {len(services)} services")
        results["get_services"] = True
    else:
        print_error(f"Get services failed: {response.status_code if response else 'No response'}")
        results["get_services"] = False
    
    # 2. Get towing services (as Admin)
    print_test("Get Towing Services (as Admin)")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    response = make_request("GET", "/towing-services", headers=admin_headers)
    
    if response and response.status_code == 200:
        towing_services = response.json()
        print_success(f"Retrieved {len(towing_services)} towing services")
        results["get_towing_services"] = True
    else:
        print_error(f"Get towing services failed: {response.status_code if response else 'No response'}")
        results["get_towing_services"] = False
    
    return results

def test_file_upload(authority_token: str):
    """Test file upload functionality"""
    print_header("FILE UPLOAD TEST")
    results = {}
    
    print_test("Photo Upload")
    headers = {"Authorization": f"Bearer {authority_token}"}
    
    # Create a simple test image in base64 format (1x1 pixel PNG)
    test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    
    # Try uploading via the jobs API (photos field)
    job_data = {
        "license_plate": f"PHOTO-{int(time.time())}",
        "tow_reason": "Test photo upload",
        "location_address": "Test Street 1, Berlin",
        "location_lat": 52.5200,
        "location_lng": 13.4050,
        "photos": [f"data:image/png;base64,{test_image_b64}"],
        "notes": "Test job with photo upload"
    }
    
    response = make_request("POST", "/jobs", headers=headers, json_data=job_data)
    
    if response and response.status_code in [200, 201]:
        job = response.json()
        photos = job.get("photos", [])
        print_success(f"Job with photo created: {len(photos)} photos uploaded")
        results["photo_upload"] = True
    else:
        print_error(f"Photo upload failed: {response.status_code if response else 'No response'}")
        results["photo_upload"] = False
    
    return results

def main():
    print_header("AbschleppPortal Backend Comprehensive Test")
    print_info(f"Backend URL: {BACKEND_URL}")
    print_info(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = {}
    
    # 1. Authentication Tests
    auth_results, tokens = test_authentication()
    all_results.update(auth_results)
    
    # Check if we have required tokens
    if not tokens.get("admin"):
        print_error("Admin login failed - cannot proceed with admin tests")
        admin_tests_possible = False
    else:
        admin_tests_possible = True
    
    if not tokens.get("authority"):
        print_error("Authority login failed - cannot proceed with jobs/services tests")
        authority_tests_possible = False
    else:
        authority_tests_possible = True
    
    time.sleep(1)
    
    # 2. Jobs API Tests
    if authority_tests_possible:
        jobs_results = test_jobs_api(tokens["authority"])
        all_results.update(jobs_results)
        time.sleep(1)
    
    # 3. Admin Endpoint Tests
    if admin_tests_possible:
        admin_results = test_admin_endpoints(tokens["admin"])
        all_results.update(admin_results)
        time.sleep(1)
    
    # 4. Services API Tests
    if admin_tests_possible and authority_tests_possible:
        services_results = test_services_api(tokens["authority"], tokens["admin"])
        all_results.update(services_results)
        time.sleep(1)
    
    # 5. File Upload Test
    if authority_tests_possible:
        upload_results = test_file_upload(tokens["authority"])
        all_results.update(upload_results)
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for result in all_results.values() if result)
    total = len(all_results)
    
    # Group results by category
    auth_tests = ["admin_login", "authority_login", "towing_login", "password_reset", "registration"]
    jobs_tests = ["get_jobs", "job_count", "create_job", "get_job_detail", "update_job"]
    admin_tests = ["get_users", "get_audit_logs", "create_backup", "list_backups", "send_test_email", "send_weekly_report", "backup_status"]
    services_tests = ["get_services", "get_towing_services"]
    upload_tests = ["photo_upload"]
    
    print_info("\n📝 AUTHENTICATION TESTS:")
    for test in auth_tests:
        if test in all_results:
            status = "✅ PASSED" if all_results[test] else "❌ FAILED"
            print_info(f"  {test}: {status}")
    
    print_info("\n📋 JOBS API TESTS:")
    for test in jobs_tests:
        if test in all_results:
            status = "✅ PASSED" if all_results[test] else "❌ FAILED"
            print_info(f"  {test}: {status}")
    
    print_info("\n👑 ADMIN ENDPOINT TESTS:")
    for test in admin_tests:
        if test in all_results:
            status = "✅ PASSED" if all_results[test] else "❌ FAILED"
            print_info(f"  {test}: {status}")
    
    print_info("\n🚚 SERVICES API TESTS:")
    for test in services_tests:
        if test in all_results:
            status = "✅ PASSED" if all_results[test] else "❌ FAILED"
            print_info(f"  {test}: {status}")
    
    print_info("\n📷 FILE UPLOAD TESTS:")
    for test in upload_tests:
        if test in all_results:
            status = "✅ PASSED" if all_results[test] else "❌ FAILED"
            print_info(f"  {test}: {status}")
    
    # Overall summary
    success_rate = (passed / total) * 100 if total > 0 else 0
    print_info(f"\n📊 OVERALL RESULTS: {passed}/{total} tests passed ({success_rate:.1f}%)")
    
    if passed == total:
        print_success("🎉 ALL TESTS PASSED - AbschleppPortal backend is fully functional!")
    elif passed >= total * 0.8:  # 80% success rate
        print_info("⚠️  MOSTLY WORKING - Some tests failed but core functionality is working")
    else:
        print_error("❌ CRITICAL ISSUES - Multiple tests failed")
    
    # List any failed tests
    failed_tests = [test for test, result in all_results.items() if not result]
    if failed_tests:
        print_error(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
        for test in failed_tests:
            print_error(f"  - {test}")
    
    return passed, total, all_results

if __name__ == "__main__":
    try:
        passed, total, results = main()
        sys.exit(0 if passed == total else 1)
    except KeyboardInterrupt:
        print_error("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
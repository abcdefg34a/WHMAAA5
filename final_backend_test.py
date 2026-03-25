#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AbschleppPortal Backend Test Report
===================================

Final comprehensive test with detailed error analysis
"""

import requests
import json
import sys
import time
import base64
from datetime import datetime
from typing import Dict, Optional

# Backend URL from frontend .env
BACKEND_URL = "https://dual-yard-system.preview.emergentagent.com/api"

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

def print_warning(message):
    print(f"⚠️  {message}")

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

def test_endpoint(name, method, endpoint, headers=None, json_data=None, expected_codes=[200]):
    """Generic endpoint test function"""
    print_test(name)
    
    response = make_request(method, endpoint, headers=headers, json_data=json_data)
    
    if not response:
        print_error("No response received")
        return False, None
    
    if response.status_code in expected_codes:
        try:
            data = response.json() if response.content else {}
            print_success(f"Success: {response.status_code}")
            return True, data
        except:
            print_success(f"Success: {response.status_code} (no JSON response)")
            return True, None
    else:
        print_error(f"Failed: {response.status_code} - {response.text[:200]}")
        return False, None

def main():
    print_header("AbschleppPortal Backend Final Test Report")
    print_info(f"Backend URL: {BACKEND_URL}")
    print_info(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    issues = []
    
    # ===== AUTHENTICATION TESTS =====
    print_header("AUTHENTICATION TESTS")
    
    # Admin Login
    success, admin_data = test_endpoint("Admin Login", "POST", "/auth/login", 
                                       json_data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    results["admin_login"] = success
    admin_token = admin_data.get("access_token") if admin_data else None
    
    # Authority Login  
    success, auth_data = test_endpoint("Authority Login", "POST", "/auth/login",
                                      json_data={"email": AUTHORITY_EMAIL, "password": AUTHORITY_PASSWORD})
    results["authority_login"] = success
    authority_token = auth_data.get("access_token") if auth_data else None
    
    # Towing Service Login
    success, towing_data = test_endpoint("Towing Service Login", "POST", "/auth/login",
                                        json_data={"email": TOWING_EMAIL, "password": TOWING_PASSWORD})
    results["towing_login"] = success
    towing_token = towing_data.get("access_token") if towing_data else None
    
    # Password Reset
    success, _ = test_endpoint("Password Reset Request", "POST", "/auth/forgot-password",
                               json_data={"email": "test@example.com"})
    results["password_reset"] = success
    
    # Registration (expects 202 - pending approval)
    test_email = f"test_{int(time.time())}@example.com"
    success, _ = test_endpoint("New Registration", "POST", "/auth/register",
                               json_data={
                                   "email": test_email,
                                   "password": "TestPass123!",
                                   "role": "authority",
                                   "name": "Test Authority",
                                   "authority_name": "Test Department",
                                   "department": "Traffic Police"
                               }, expected_codes=[200, 202])
    results["registration"] = success
    
    # ===== JOBS API TESTS (as Authority) =====
    print_header("JOBS API TESTS")
    
    if not authority_token:
        print_error("No authority token - skipping Jobs API tests")
        issues.append("Authority login failed - cannot test Jobs API")
    else:
        auth_headers = {"Authorization": f"Bearer {authority_token}"}
        
        # Get Jobs
        success, jobs_data = test_endpoint("Get All Jobs", "GET", "/jobs", headers=auth_headers)
        results["get_jobs"] = success
        if success and jobs_data:
            print_info(f"Found {len(jobs_data)} jobs")
        
        # Get Job Count
        success, count_data = test_endpoint("Get Job Count", "GET", "/jobs/count/total", headers=auth_headers)
        results["job_count"] = success
        
        # Create Job
        job_data = {
            "license_plate": f"TEST-{int(time.time())}",
            "tow_reason": "Falschparken",
            "location_address": "Musterstraße 123, Berlin",
            "location_lat": 52.5200,
            "location_lng": 13.4050,
            "notes": "Test job created by automated test"
        }
        success, created_job = test_endpoint("Create New Job", "POST", "/jobs", 
                                            headers=auth_headers, json_data=job_data, expected_codes=[200, 201])
        results["create_job"] = success
        
        if success and created_job:
            job_id = created_job.get("id")
            job_number = created_job.get("job_number")
            print_info(f"Created job: {job_number} (ID: {job_id})")
            
            # Get Specific Job
            success, _ = test_endpoint(f"Get Job {job_id}", "GET", f"/jobs/{job_id}", headers=auth_headers)
            results["get_job_detail"] = success
            
            # Update Job
            success, _ = test_endpoint(f"Update Job {job_id}", "PUT", f"/jobs/{job_id}",
                                     headers=auth_headers, 
                                     json_data={"status": "assigned", "notes": "Updated by test"})
            results["update_job"] = success
        else:
            results["get_job_detail"] = False
            results["update_job"] = False
    
    # ===== ADMIN ENDPOINTS =====
    print_header("ADMIN ENDPOINTS TESTS")
    
    if not admin_token:
        print_error("No admin token - skipping Admin tests")
        issues.append("Admin login failed - cannot test Admin endpoints")
    else:
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get Users
        success, users_data = test_endpoint("Get All Users", "GET", "/admin/users", headers=admin_headers)
        results["get_users"] = success
        if success and users_data:
            print_info(f"Found {len(users_data)} users")
        
        # Get Audit Logs (known issue with missing user_name fields)
        print_test("Get Audit Logs")
        response = make_request("GET", "/admin/audit-logs", headers=admin_headers)
        if response and response.status_code == 500:
            print_warning("Audit logs endpoint has validation error (some logs missing user_name field)")
            print_error(f"Failed: {response.status_code} - Pydantic validation error")
            results["get_audit_logs"] = False
            issues.append("Audit logs endpoint failing due to missing user_name fields in some log entries")
        elif response and response.status_code == 200:
            print_success("Audit logs retrieved successfully")
            results["get_audit_logs"] = True
        else:
            print_error(f"Unexpected response: {response.status_code if response else 'No response'}")
            results["get_audit_logs"] = False
        
        # Database Backup
        success, backup_data = test_endpoint("Create Database Backup", "POST", "/admin/backup", headers=admin_headers)
        results["create_backup"] = success
        
        # List Backups
        success, backups_data = test_endpoint("List All Backups", "GET", "/admin/backups", headers=admin_headers)
        results["list_backups"] = success
        if success and backups_data:
            backup_count = len(backups_data) if isinstance(backups_data, list) else len(backups_data.get('backups', []))
            print_info(f"Found {backup_count} backups")
        
        # Send Test Email
        success, _ = test_endpoint("Send Test Email", "POST", "/admin/backups/send-test-email", headers=admin_headers)
        results["send_test_email"] = success
        
        # Send Weekly Report
        success, _ = test_endpoint("Send Weekly Report", "POST", "/admin/backups/send-weekly-report", headers=admin_headers)
        results["send_weekly_report"] = success
        
        # Backup Status - This endpoint doesn't exist
        print_test("Get Backup Status")
        response = make_request("GET", "/admin/backups/status", headers=admin_headers)
        if response and response.status_code == 404:
            print_warning("Backup status endpoint not implemented")
            results["backup_status"] = False
            issues.append("GET /api/admin/backups/status endpoint is not implemented")
        else:
            print_error(f"Unexpected response: {response.status_code if response else 'No response'}")
            results["backup_status"] = False
    
    # ===== SERVICES API TESTS =====  
    print_header("SERVICES API TESTS")
    
    # Get Services (as Authority)
    if authority_token:
        success, services_data = test_endpoint("Get Services (as Authority)", "GET", "/services", 
                                              headers={"Authorization": f"Bearer {authority_token}"})
        results["get_services"] = success
        if success and services_data:
            print_info(f"Found {len(services_data)} services")
    else:
        results["get_services"] = False
    
    # Get Towing Services (as Admin) - This endpoint doesn't exist as /towing-services
    if admin_token:
        print_test("Get Towing Services (as Admin)")
        response = make_request("GET", "/towing-services", headers={"Authorization": f"Bearer {admin_token}"})
        if response and response.status_code == 404:
            print_warning("Towing services endpoint not found - use /services or /admin/pending-services instead")
            results["get_towing_services"] = False
            issues.append("GET /api/towing-services endpoint is not implemented. Use /api/services or /api/admin/pending-services")
            
            # Try alternative endpoint
            success, _ = test_endpoint("Get Pending Services (Admin)", "GET", "/admin/pending-services", 
                                     headers={"Authorization": f"Bearer {admin_token}"})
            results["get_pending_services"] = success
        else:
            print_error(f"Unexpected response: {response.status_code if response else 'No response'}")
            results["get_towing_services"] = False
    else:
        results["get_towing_services"] = False
    
    # ===== FILE UPLOAD TEST =====
    print_header("FILE UPLOAD TEST")
    
    if authority_token:
        # Test photo upload via job creation
        print_test("Photo Upload via Job Creation")
        test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        
        job_data = {
            "license_plate": f"PHOTO-{int(time.time())}",
            "tow_reason": "Test photo upload",
            "location_address": "Test Street 1, Berlin",
            "location_lat": 52.5200,
            "location_lng": 13.4050,
            "photos": [f"data:image/png;base64,{test_image_b64}"],
            "notes": "Test job with photo upload"
        }
        
        success, photo_job = test_endpoint("Create Job with Photo", "POST", "/jobs",
                                         headers={"Authorization": f"Bearer {authority_token}"},
                                         json_data=job_data, expected_codes=[200, 201])
        results["photo_upload"] = success
        
        if success and photo_job:
            photos = photo_job.get("photos", [])
            print_info(f"Job created with {len(photos)} photos")
            if len(photos) > 0:
                print_success("Photo upload functionality working")
            else:
                print_warning("Job created but no photos attached")
    else:
        results["photo_upload"] = False
    
    # ===== FINAL SUMMARY =====
    print_header("FINAL TEST SUMMARY")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    success_rate = (passed / total) * 100 if total > 0 else 0
    
    print_info(f"📊 OVERALL RESULTS: {passed}/{total} tests passed ({success_rate:.1f}%)")
    
    # Categorize results
    categories = {
        "Authentication": ["admin_login", "authority_login", "towing_login", "password_reset", "registration"],
        "Jobs API": ["get_jobs", "job_count", "create_job", "get_job_detail", "update_job"],
        "Admin Endpoints": ["get_users", "get_audit_logs", "create_backup", "list_backups", 
                           "send_test_email", "send_weekly_report", "backup_status"],
        "Services": ["get_services", "get_towing_services", "get_pending_services"],
        "File Upload": ["photo_upload"]
    }
    
    for category, tests in categories.items():
        category_passed = sum(1 for test in tests if results.get(test, False))
        category_total = sum(1 for test in tests if test in results)
        if category_total > 0:
            category_rate = (category_passed / category_total) * 100
            status = "✅" if category_rate == 100 else "⚠️" if category_rate >= 80 else "❌"
            print_info(f"{status} {category}: {category_passed}/{category_total} ({category_rate:.0f}%)")
    
    # Report critical issues
    if issues:
        print_header("IDENTIFIED ISSUES")
        for i, issue in enumerate(issues, 1):
            print_error(f"{i}. {issue}")
    
    # Overall assessment
    if success_rate >= 90:
        print_success("🎉 EXCELLENT - AbschleppPortal backend is highly functional!")
    elif success_rate >= 80:
        print_success("✅ GOOD - Core functionality working with minor issues")
    elif success_rate >= 60:
        print_warning("⚠️  ACCEPTABLE - Most features working but several issues need attention")
    else:
        print_error("❌ CRITICAL - Multiple core features failing")
    
    return passed, total, results, issues

if __name__ == "__main__":
    try:
        passed, total, results, issues = main()
        sys.exit(0 if passed >= total * 0.8 else 1)  # 80% pass rate required
    except KeyboardInterrupt:
        print_error("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
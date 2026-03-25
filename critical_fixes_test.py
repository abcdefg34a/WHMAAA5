#!/usr/bin/env python3
"""
Critical Fixes Test Suite for AbschleppPortal
Tests the two specific critical fixes:
1. Audit Logs Fix (GET /api/admin/audit-logs)
2. Job Update Fix (PUT /api/jobs/{job_id} and PATCH /api/jobs/{job_id})
"""

import requests
import json
import sys
import os
from datetime import datetime
import uuid

# Get backend URL from environment
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://dual-yard-system.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

# Test credentials from review request
ADMIN_CREDENTIALS = {
    "email": "admin@test.de",
    "password": "Admin123!"
}

AUTHORITY_CREDENTIALS = {
    "email": "behoerde@test.de", 
    "password": "Behoerde123!"
}

TOWING_SERVICE_CREDENTIALS = {
    "email": "abschlepp@test.de",
    "password": "Abschlepp123!"
}

class CriticalFixesTest:
    def __init__(self):
        self.admin_token = None
        self.authority_token = None
        self.towing_token = None
        self.test_job_id = None
        self.test_results = []
        
    def log_result(self, test_name, success, details=""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        
    def make_request(self, method, endpoint, data=None, token=None, expected_status=200, timeout=30):
        """Make HTTP request with error handling"""
        url = f"{API_BASE}{endpoint}"
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=timeout)
            elif method.upper() == "PATCH":
                response = requests.patch(url, headers=headers, json=data, timeout=timeout)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            print(f"Request: {method} {endpoint} -> Status: {response.status_code}")
            
            if response.status_code != expected_status:
                print(f"Expected status {expected_status}, got {response.status_code}")
                print(f"Response: {response.text}")
                return None, response.status_code
                
            return response.json() if response.content else {}, response.status_code
            
        except requests.exceptions.Timeout:
            print(f"Request timed out after {timeout} seconds")
            return None, 408  # Request Timeout
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None, 0
            
    def test_1_admin_login(self):
        """Test 1: Admin Login"""
        print("\n=== Test 1: Admin Login ===")
        
        response, status = self.make_request(
            "POST", "/auth/login", 
            ADMIN_CREDENTIALS,
            expected_status=200
        )
        
        if response and "access_token" in response:
            self.admin_token = response["access_token"]
            self.log_result("Admin Login", True, f"Token received for admin user")
            return True
        else:
            self.log_result("Admin Login", False, f"Login failed with status {status}")
            return False
            
    def test_2_audit_logs_fix(self):
        """Test 2: Audit Logs Fix - GET /api/admin/audit-logs should work without Pydantic validation errors"""
        print("\n=== Test 2: Audit Logs Fix ===")
        
        if not self.admin_token:
            self.log_result("Audit Logs Fix", False, "No admin token available")
            return False
            
        response, status = self.make_request(
            "GET", "/admin/audit-logs",
            token=self.admin_token,
            expected_status=200,
            timeout=30
        )
        
        if response is not None and status == 200:
            # Check if response contains audit logs
            if isinstance(response, list):
                log_count = len(response)
                self.log_result("Audit Logs Fix", True, 
                              f"Successfully retrieved {log_count} audit logs without Pydantic validation errors")
                return True
            elif isinstance(response, dict) and "logs" in response:
                log_count = len(response["logs"])
                self.log_result("Audit Logs Fix", True, 
                              f"Successfully retrieved {log_count} audit logs without Pydantic validation errors")
                return True
            else:
                self.log_result("Audit Logs Fix", False, 
                              f"Unexpected response format: {type(response)}")
                return False
        else:
            self.log_result("Audit Logs Fix", False, 
                          f"Failed with status {status}. Previous issue was Pydantic validation error with missing user_name fields")
            return False
            
    def test_3_towing_service_login(self):
        """Test 3: Towing Service Login"""
        print("\n=== Test 3: Towing Service Login ===")
        
        response, status = self.make_request(
            "POST", "/auth/login", 
            TOWING_SERVICE_CREDENTIALS,
            expected_status=200
        )
        
        if response and "access_token" in response:
            self.towing_token = response["access_token"]
            self.log_result("Towing Service Login", True, f"Token received for towing service")
            return True
        else:
            self.log_result("Towing Service Login", False, f"Login failed with status {status}")
            return False
            
    def test_4_get_jobs_for_update(self):
        """Test 4: Get Jobs to find one for update testing"""
        print("\n=== Test 4: Get Jobs for Update Testing ===")
        
        if not self.towing_token:
            self.log_result("Get Jobs for Update", False, "No towing service token available")
            return False
            
        response, status = self.make_request(
            "GET", "/jobs",
            token=self.towing_token,
            expected_status=200
        )
        
        if response and isinstance(response, list) and len(response) > 0:
            # Look for a job with status 'assigned' or 'on_site' that can be updated
            suitable_job = None
            for job in response:
                if job.get("status") in ["assigned", "on_site", "pending"]:
                    suitable_job = job
                    break
                    
            if suitable_job:
                self.test_job_id = suitable_job["id"]
                job_number = suitable_job.get("job_number", "N/A")
                current_status = suitable_job.get("status", "unknown")
                self.log_result("Get Jobs for Update", True, 
                              f"Found job {job_number} (ID: {self.test_job_id}) with status '{current_status}' for update testing")
                return True
            else:
                self.log_result("Get Jobs for Update", False, 
                              "No suitable jobs found with status 'assigned', 'on_site', or 'pending'")
                return False
        else:
            self.log_result("Get Jobs for Update", False, f"Failed to get jobs with status {status}")
            return False
            
    def test_5_job_update_put_fix(self):
        """Test 5: Job Update Fix - PUT /api/jobs/{job_id} should work without timeout"""
        print("\n=== Test 5: Job Update PUT Fix ===")
        
        if not self.towing_token or not self.test_job_id:
            self.log_result("Job Update PUT Fix", False, "No towing service token or test job ID available")
            return False
            
        update_data = {
            "status": "on_site"
        }
        
        response, status = self.make_request(
            "PUT", f"/jobs/{self.test_job_id}",
            data=update_data,
            token=self.towing_token,
            expected_status=200,
            timeout=30  # Previous issue was timeout
        )
        
        if response is not None and status == 200:
            updated_status = response.get("status", "unknown")
            if updated_status == "on_site":
                self.log_result("Job Update PUT Fix", True, 
                              f"Successfully updated job status to 'on_site' without timeout")
                return True
            else:
                self.log_result("Job Update PUT Fix", False, 
                              f"Job updated but status is '{updated_status}', expected 'on_site'")
                return False
        elif status == 408:  # Timeout
            self.log_result("Job Update PUT Fix", False, 
                          "Request timed out - the original timeout issue still exists")
            return False
        else:
            self.log_result("Job Update PUT Fix", False, 
                          f"Failed with status {status}. Previous issue was timeout or network issue")
            return False
            
    def test_6_job_update_patch_fix(self):
        """Test 6: Job Update Fix - PATCH /api/jobs/{job_id} should work without timeout"""
        print("\n=== Test 6: Job Update PATCH Fix ===")
        
        if not self.towing_token or not self.test_job_id:
            self.log_result("Job Update PATCH Fix", False, "No towing service token or test job ID available")
            return False
            
        update_data = {
            "status": "towed"
        }
        
        response, status = self.make_request(
            "PATCH", f"/jobs/{self.test_job_id}",
            data=update_data,
            token=self.towing_token,
            expected_status=200,
            timeout=30  # Previous issue was timeout
        )
        
        if response is not None and status == 200:
            updated_status = response.get("status", "unknown")
            if updated_status == "towed":
                self.log_result("Job Update PATCH Fix", True, 
                              f"Successfully updated job status to 'towed' without timeout")
                return True
            else:
                self.log_result("Job Update PATCH Fix", False, 
                              f"Job updated but status is '{updated_status}', expected 'towed'")
                return False
        elif status == 408:  # Timeout
            self.log_result("Job Update PATCH Fix", False, 
                          "Request timed out - the original timeout issue still exists")
            return False
        else:
            self.log_result("Job Update PATCH Fix", False, 
                          f"Failed with status {status}. Previous issue was timeout or network issue")
            return False
            
    def run_all_tests(self):
        """Run all critical fixes tests"""
        print("🚀 Starting Critical Fixes Tests for AbschleppPortal")
        print(f"Backend URL: {BACKEND_URL}")
        print("Testing two specific critical fixes:")
        print("1. Audit Logs Fix (GET /api/admin/audit-logs)")
        print("2. Job Update Fix (PUT /api/jobs/{job_id} and PATCH /api/jobs/{job_id})")
        print("=" * 80)
        
        tests = [
            self.test_1_admin_login,
            self.test_2_audit_logs_fix,
            self.test_3_towing_service_login,
            self.test_4_get_jobs_for_update,
            self.test_5_job_update_put_fix,
            self.test_6_job_update_patch_fix
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                print(f"❌ Test failed with exception: {e}")
                self.log_result(test.__name__, False, f"Exception: {e}")
                
        print("\n" + "=" * 80)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All critical fixes tests PASSED!")
            return True
        else:
            print(f"⚠️  {total - passed} test(s) FAILED")
            return False

def main():
    """Main test runner"""
    tester = CriticalFixesTest()
    success = tester.run_all_tests()
    
    # Print detailed results
    print("\n📋 Detailed Test Results:")
    for result in tester.test_results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['test']}")
        if result["details"]:
            print(f"   {result['details']}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class GoLiveFeatureTester:
    def __init__(self, base_url="https://pg-abschlepp-core.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # Test credentials as specified in the request
        self.admin_credentials = {
            "email": "admin@test.de",
            "password": "Admin123!"
        }
        
        # Test data for job creation (needed for pagination tests)
        self.test_authority = {
            "email": f"test_authority_{datetime.now().strftime('%H%M%S')}@test.de",
            "password": "TestPass123!",
            "name": "Test Authority",
            "role": "authority",
            "authority_name": "Test Ordnungsamt",
            "department": "Verkehrsüberwachung"
        }
        
        self.authority_token = None
        self.created_job_ids = []

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Optional[Dict] = None, token: Optional[str] = None) -> tuple[bool, Dict]:
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            success = response.status_code == expected_status
            result = {
                'test': name,
                'method': method,
                'endpoint': endpoint,
                'expected_status': expected_status,
                'actual_status': response.status_code,
                'success': success
            }
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    result['response_data'] = response_data
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    result['error'] = error_data
                    print(f"   Error: {error_data}")
                except:
                    result['error'] = response.text
                    print(f"   Error: {response.text}")
                
            self.test_results.append(result)
            return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            result = {
                'test': name,
                'method': method,
                'endpoint': endpoint,
                'expected_status': expected_status,
                'actual_status': 'ERROR',
                'success': False,
                'error': str(e)
            }
            self.test_results.append(result)
            return False, {}

    def test_admin_login_and_audit(self):
        """Test admin login and verify audit log entry is created"""
        print("\n🔐 Testing Admin Login and Audit Logging...")
        
        # First, get initial audit log count
        if self.admin_token:
            success, response = self.run_test(
                "Get Initial Audit Log Count", "GET", "admin/audit-logs/count", 200,
                token=self.admin_token
            )
            initial_count = response.get('total', 0) if success else 0
        else:
            initial_count = 0
        
        # Test admin login
        success, response = self.run_test(
            "Admin Login", "POST", "auth/login", 200, self.admin_credentials
        )
        
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            user_data = response.get('user', {})
            print(f"   Admin logged in successfully")
            print(f"   User ID: {user_data.get('id')}")
            print(f"   User Role: {user_data.get('role')}")
            
            # Wait a moment for audit log to be written
            time.sleep(1)
            
            # Check if audit log entry was created
            success, audit_response = self.run_test(
                "Get Audit Logs After Login", "GET", "admin/audit-logs", 200,
                token=self.admin_token
            )
            
            if success and audit_response:
                # Look for recent login event
                login_events = [log for log in audit_response if log.get('action') == 'USER_LOGIN']
                recent_login = None
                
                for event in login_events:
                    if event.get('user_id') == user_data.get('id'):
                        recent_login = event
                        break
                
                if recent_login:
                    print(f"   ✅ Audit log entry found for login")
                    print(f"   - Action: {recent_login.get('action')}")
                    print(f"   - User: {recent_login.get('user_name')}")
                    print(f"   - Timestamp: {recent_login.get('timestamp')}")
                    print(f"   - Details: {recent_login.get('details', {})}")
                else:
                    print(f"   ❌ No audit log entry found for admin login")
            
            return True
        else:
            print(f"   ❌ Admin login failed")
            return False

    def test_failed_login_audit(self):
        """Test failed login and verify LOGIN_FAILED audit entry"""
        print("\n🚫 Testing Failed Login Audit Logging...")
        
        # Get initial audit log count
        success, response = self.run_test(
            "Get Audit Logs Before Failed Login", "GET", "admin/audit-logs", 200,
            token=self.admin_token
        )
        initial_failed_count = 0
        if success and response:
            initial_failed_count = len([log for log in response if log.get('action') == 'LOGIN_FAILED'])
        
        # Attempt login with wrong password
        wrong_credentials = {
            "email": "admin@test.de",
            "password": "WrongPassword123!"
        }
        
        success, response = self.run_test(
            "Failed Login Attempt", "POST", "auth/login", 401, wrong_credentials
        )
        
        if success:  # Success means we got the expected 401 status
            print(f"   ✅ Failed login correctly rejected")
            
            # Wait a moment for audit log to be written
            time.sleep(1)
            
            # Check if LOGIN_FAILED audit entry was created
            success, audit_response = self.run_test(
                "Get Audit Logs After Failed Login", "GET", "admin/audit-logs", 200,
                token=self.admin_token
            )
            
            if success and audit_response:
                failed_login_events = [log for log in audit_response if log.get('action') == 'LOGIN_FAILED']
                
                if len(failed_login_events) > initial_failed_count:
                    recent_failed = failed_login_events[0]  # Most recent should be first
                    print(f"   ✅ LOGIN_FAILED audit entry found")
                    print(f"   - Action: {recent_failed.get('action')}")
                    print(f"   - User: {recent_failed.get('user_name')}")
                    print(f"   - Timestamp: {recent_failed.get('timestamp')}")
                    print(f"   - Details: {recent_failed.get('details', {})}")
                    
                    # Check if details contain expected information
                    details = recent_failed.get('details', {})
                    if details.get('email') == wrong_credentials['email'] and details.get('reason') == 'invalid_credentials':
                        print(f"   ✅ Failed login audit contains correct details")
                    else:
                        print(f"   ❌ Failed login audit missing expected details")
                else:
                    print(f"   ❌ No new LOGIN_FAILED audit entry found")
            
            return True
        else:
            print(f"   ❌ Failed login test did not behave as expected")
            return False

    def setup_test_data(self):
        """Create test authority and jobs for pagination testing"""
        print("\n📋 Setting up test data for pagination tests...")
        
        # Register test authority
        success, response = self.run_test(
            "Register Test Authority", "POST", "auth/register", 200, self.test_authority
        )
        
        if success and 'access_token' in response:
            self.authority_token = response['access_token']
            authority_id = response.get('user', {}).get('id')
            
            # Approve the authority using admin token
            approval_data = {"approved": True}
            success, response = self.run_test(
                "Approve Test Authority", "POST", f"admin/approve-authority/{authority_id}", 200,
                approval_data, self.admin_token
            )
            
            if success:
                print(f"   ✅ Test authority approved")
                
                # Create several test jobs for pagination
                for i in range(8):  # Create 8 jobs to test pagination
                    job_data = {
                        "license_plate": f"B-PAGE{i:03d}",
                        "vin": f"WVWZZZ3CZWE12345{i}",
                        "tow_reason": f"Pagination test job {i+1}",
                        "location_address": f"Teststraße {i+1}, 12345 Berlin",
                        "location_lat": 52.520008 + i * 0.001,
                        "location_lng": 13.404954 + i * 0.001,
                        "notes": f"Job {i+1} for pagination testing"
                    }
                    
                    success, job_response = self.run_test(
                        f"Create Test Job {i+1}", "POST", "jobs", 200,
                        job_data, self.authority_token
                    )
                    
                    if success and 'id' in job_response:
                        self.created_job_ids.append(job_response['id'])
                
                print(f"   ✅ Created {len(self.created_job_ids)} test jobs")
                return True
            else:
                print(f"   ❌ Failed to approve test authority")
                return False
        else:
            print(f"   ❌ Failed to register test authority")
            return False

    def test_admin_jobs_pagination(self):
        """Test GET /api/admin/jobs pagination"""
        print("\n📄 Testing Admin Jobs Pagination...")
        
        # Test 1: Get jobs with page=1&limit=5
        success, response = self.run_test(
            "Admin Jobs - Page 1, Limit 5", "GET", "admin/jobs?page=1&limit=5", 200,
            token=self.admin_token
        )
        
        if success and response:
            job_count = len(response)
            print(f"   Page 1 returned {job_count} jobs")
            
            if job_count <= 5:
                print(f"   ✅ Pagination limit respected (≤5 jobs returned)")
            else:
                print(f"   ❌ Pagination limit not respected ({job_count} > 5)")
            
            # Store first page jobs for comparison
            first_page_jobs = [job.get('id') for job in response]
        
        # Test 2: Get jobs with page=2&limit=5
        success, response = self.run_test(
            "Admin Jobs - Page 2, Limit 5", "GET", "admin/jobs?page=2&limit=5", 200,
            token=self.admin_token
        )
        
        if success and response:
            job_count = len(response)
            print(f"   Page 2 returned {job_count} jobs")
            
            if job_count <= 5:
                print(f"   ✅ Pagination limit respected on page 2")
            else:
                print(f"   ❌ Pagination limit not respected on page 2")
            
            # Check that page 2 jobs are different from page 1
            second_page_jobs = [job.get('id') for job in response]
            if len(set(first_page_jobs) & set(second_page_jobs)) == 0:
                print(f"   ✅ Page 2 contains different jobs than page 1")
            else:
                print(f"   ❌ Page 2 contains duplicate jobs from page 1")
        
        # Test 3: Test different limit values
        success, response = self.run_test(
            "Admin Jobs - Limit 3", "GET", "admin/jobs?page=1&limit=3", 200,
            token=self.admin_token
        )
        
        if success and response:
            job_count = len(response)
            print(f"   Limit 3 returned {job_count} jobs")
            
            if job_count <= 3:
                print(f"   ✅ Custom limit (3) respected")
            else:
                print(f"   ❌ Custom limit (3) not respected")
        
        # Test 4: Test without pagination parameters (should use defaults)
        success, response = self.run_test(
            "Admin Jobs - No Pagination Params", "GET", "admin/jobs", 200,
            token=self.admin_token
        )
        
        if success and response:
            job_count = len(response)
            print(f"   Default pagination returned {job_count} jobs")
            
            # Should use default limit (likely 50)
            if job_count <= 50:
                print(f"   ✅ Default pagination working")
            else:
                print(f"   ❌ Default pagination may not be working")
        
        return True

    def test_admin_jobs_count(self):
        """Test GET /api/admin/jobs/count"""
        print("\n🔢 Testing Admin Jobs Count Endpoint...")
        
        success, response = self.run_test(
            "Admin Jobs Count", "GET", "admin/jobs/count", 200,
            token=self.admin_token
        )
        
        if success and response:
            total_count = response.get('total')
            print(f"   Total jobs count: {total_count}")
            
            if isinstance(total_count, int) and total_count >= 0:
                print(f"   ✅ Jobs count endpoint returns valid integer")
                
                # Verify count matches actual jobs by getting all jobs
                success, all_jobs_response = self.run_test(
                    "Admin All Jobs for Verification", "GET", "admin/jobs?limit=1000", 200,
                    token=self.admin_token
                )
                
                if success and all_jobs_response:
                    actual_count = len(all_jobs_response)
                    print(f"   Actual jobs retrieved: {actual_count}")
                    
                    if total_count == actual_count:
                        print(f"   ✅ Count endpoint matches actual job count")
                    else:
                        print(f"   ❌ Count mismatch - Count endpoint: {total_count}, Actual: {actual_count}")
                
                return True
            else:
                print(f"   ❌ Jobs count endpoint returns invalid data: {total_count}")
                return False
        else:
            print(f"   ❌ Jobs count endpoint failed")
            return False

    def test_jobs_count_total(self):
        """Test GET /api/jobs/count/total (with auth)"""
        print("\n📊 Testing Jobs Count Total Endpoint...")
        
        # Test with admin token
        success, response = self.run_test(
            "Jobs Count Total - Admin", "GET", "jobs/count/total", 200,
            token=self.admin_token
        )
        
        if success and response:
            admin_total = response.get('total')
            print(f"   Admin sees total: {admin_total} jobs")
            
            if isinstance(admin_total, int) and admin_total >= 0:
                print(f"   ✅ Admin jobs count/total returns valid integer")
            else:
                print(f"   ❌ Admin jobs count/total returns invalid data")
        
        # Test with authority token (should see only their jobs)
        if self.authority_token:
            success, response = self.run_test(
                "Jobs Count Total - Authority", "GET", "jobs/count/total", 200,
                token=self.authority_token
            )
            
            if success and response:
                authority_total = response.get('total')
                print(f"   Authority sees total: {authority_total} jobs")
                
                if isinstance(authority_total, int) and authority_total >= 0:
                    print(f"   ✅ Authority jobs count/total returns valid integer")
                    
                    # Authority should see fewer or equal jobs than admin
                    if authority_total <= admin_total:
                        print(f"   ✅ Authority sees appropriate subset of jobs")
                    else:
                        print(f"   ❌ Authority sees more jobs than admin (unexpected)")
                else:
                    print(f"   ❌ Authority jobs count/total returns invalid data")
        
        # Test without authentication (should fail)
        success, response = self.run_test(
            "Jobs Count Total - No Auth", "GET", "jobs/count/total", 403
        )
        
        if success:  # Success means we got expected 403
            print(f"   ✅ Jobs count/total correctly requires authentication")
        
        return True

    def test_audit_logs_pagination(self):
        """Test audit logs pagination"""
        print("\n📋 Testing Audit Logs Pagination...")
        
        # Test audit logs with pagination
        success, response = self.run_test(
            "Audit Logs - Page 1, Limit 10", "GET", "admin/audit-logs?page=1&limit=10", 200,
            token=self.admin_token
        )
        
        if success and response:
            log_count = len(response)
            print(f"   Audit logs page 1 returned {log_count} entries")
            
            if log_count <= 10:
                print(f"   ✅ Audit logs pagination limit respected")
            else:
                print(f"   ❌ Audit logs pagination limit not respected")
        
        # Test audit logs count
        success, response = self.run_test(
            "Audit Logs Count", "GET", "admin/audit-logs/count", 200,
            token=self.admin_token
        )
        
        if success and response:
            # The endpoint returns 'count' not 'total'
            total_logs = response.get('count') or response.get('total')
            print(f"   Total audit logs: {total_logs}")
            
            if isinstance(total_logs, int) and total_logs >= 0:
                print(f"   ✅ Audit logs count returns valid integer")
            else:
                print(f"   ❌ Audit logs count returns invalid data")
        
        return True

    def run_go_live_tests(self):
        """Run all Go-Live feature tests"""
        print("🚀 Starting Go-Live Feature Package Tests...")
        print(f"📡 Testing against: {self.base_url}")
        print("="*60)
        
        try:
            # Test 1: Admin login and audit logging
            if not self.test_admin_login_and_audit():
                print("❌ Admin login/audit test failed")
                return False
            
            # Test 2: Failed login audit logging
            self.test_failed_login_audit()
            
            # Test 3: Setup test data for pagination
            if not self.setup_test_data():
                print("❌ Test data setup failed - pagination tests may be limited")
            
            # Test 4: Admin jobs pagination
            self.test_admin_jobs_pagination()
            
            # Test 5: Admin jobs count
            self.test_admin_jobs_count()
            
            # Test 6: Jobs count total endpoint
            self.test_jobs_count_total()
            
            # Test 7: Audit logs pagination
            self.test_audit_logs_pagination()
            
            return True
            
        except Exception as e:
            print(f"❌ Go-Live test suite failed with error: {str(e)}")
            return False

    def print_summary(self):
        """Print test summary"""
        print(f"\n📊 Go-Live Feature Test Results:")
        print("="*60)
        print(f"   Tests run: {self.tests_run}")
        print(f"   Tests passed: {self.tests_passed}")
        print(f"   Tests failed: {self.tests_run - self.tests_passed}")
        
        if self.tests_run > 0:
            success_rate = (self.tests_passed/self.tests_run*100)
            print(f"   Success rate: {success_rate:.1f}%")
        
        # Print failed tests
        failed_tests = [r for r in self.test_results if not r['success']]
        if failed_tests:
            print(f"\n❌ Failed Tests:")
            for test in failed_tests:
                print(f"   - {test['test']}: Expected {test['expected_status']}, got {test['actual_status']}")
                if 'error' in test:
                    error_msg = test['error']
                    if isinstance(error_msg, dict):
                        error_msg = error_msg.get('detail', str(error_msg))
                    print(f"     Error: {error_msg}")
        else:
            print(f"\n✅ All tests passed!")

def main():
    tester = GoLiveFeatureTester()
    
    success = tester.run_go_live_tests()
    tester.print_summary()
    
    return 0 if success and tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
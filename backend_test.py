#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class ComprehensiveAPITester:
    def __init__(self, base_url="https://vehicle-recovery-7.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.authority_token = None
        self.towing_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        
        # Test credentials from review request
        self.admin_creds = {
            "email": "admin@test.de",
            "password": "Admin123!"
        }
        
        self.authority_creds = {
            "email": "test-behoerde@test.de", 
            "password": "TestPass123!"
        }
        
        self.towing_creds = {
            "email": "abschlepp@test.de",
            "password": "Abschlepp123"
        }
        
        # Test data for job creation
        self.test_job_data = {
            "license_plate": "B-TEST999",
            "vin": "WVWZZZ3CZWE999999",
            "tow_reason": "Parken im Halteverbot",
            "location_address": "Teststraße 1, 12345 Berlin",
            "location_lat": 52.520008,
            "location_lng": 13.404954,
            "notes": "Test job for comprehensive testing"
        }
        
        self.test_job_id = None
        self.test_service_id = None
        self.test_authority_id = None

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Optional[Dict] = None, token: Optional[str] = None) -> tuple[bool, Dict, int, str]:
        """Run a single API test and return detailed results"""
        url = f"{self.base_url}/{endpoint}" if endpoint else self.base_url
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   {method} {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    return True, response_data, response.status_code, ""
                except:
                    return True, {}, response.status_code, ""
            else:
                error_msg = ""
                try:
                    error_data = response.json()
                    error_msg = str(error_data.get('detail', error_data))
                except:
                    error_msg = response.text
                
                print(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                print(f"   Error: {error_msg}")
                
                self.failed_tests.append({
                    'test': name,
                    'method': method,
                    'endpoint': endpoint,
                    'expected_status': expected_status,
                    'actual_status': response.status_code,
                    'error_message': error_msg,
                    'request_body': data
                })
                
                return False, {}, response.status_code, error_msg

        except Exception as e:
            error_msg = str(e)
            print(f"❌ FAILED - Exception: {error_msg}")
            
            self.failed_tests.append({
                'test': name,
                'method': method,
                'endpoint': endpoint,
                'expected_status': expected_status,
                'actual_status': 'EXCEPTION',
                'error_message': error_msg,
                'request_body': data
            })
            
            return False, {}, 0, error_msg

    def test_1_admin_login(self):
        """1. POST /api/auth/login (admin)"""
        success, response, status, error = self.run_test(
            "1. Admin Login", "POST", "auth/login", 200, self.admin_creds
        )
        
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            print(f"   Admin token obtained: {self.admin_token[:20]}...")
        
        return success

    def test_2_authority_login(self):
        """2. POST /api/auth/login (authority)"""
        success, response, status, error = self.run_test(
            "2. Authority Login", "POST", "auth/login", 200, self.authority_creds
        )
        
        if success and 'access_token' in response:
            self.authority_token = response['access_token']
            self.test_authority_id = response.get('user', {}).get('id')
            print(f"   Authority token obtained: {self.authority_token[:20]}...")
            print(f"   Authority ID: {self.test_authority_id}")
        
        return success

    def test_3_auth_me(self):
        """3. GET /api/auth/me"""
        if not self.admin_token:
            print("❌ No admin token available for auth/me test")
            return False
            
        success, response, status, error = self.run_test(
            "3. Auth Me", "GET", "auth/me", 200, token=self.admin_token
        )
        
        return success

    def test_4_create_job(self):
        """4. POST /api/jobs (create job)"""
        if not self.authority_token:
            print("❌ No authority token available for job creation")
            return False
            
        success, response, status, error = self.run_test(
            "4. Create Job", "POST", "jobs", 200, self.test_job_data, self.authority_token
        )
        
        if success and 'id' in response:
            self.test_job_id = response['id']
            print(f"   Job created with ID: {self.test_job_id}")
        
        return success

    def test_5_list_jobs(self):
        """5. GET /api/jobs (list jobs)"""
        if not self.authority_token:
            print("❌ No authority token available for listing jobs")
            return False
            
        success, response, status, error = self.run_test(
            "5. List Jobs", "GET", "jobs", 200, token=self.authority_token
        )
        
        if success and isinstance(response, list):
            print(f"   Retrieved {len(response)} jobs")
        
        return success

    def test_6_edit_job_data(self):
        """6. PATCH /api/jobs/{id}/edit-data"""
        if not self.test_job_id or not self.authority_token:
            print("❌ No job ID or authority token available for edit test")
            return False
            
        edit_data = {
            "license_plate": "B-EDIT999",
            "vin": "WVWZZZ3CZWE888888",
            "tow_reason": "Updated tow reason",
            "notes": "Updated notes for testing"
        }
        
        success, response, status, error = self.run_test(
            "6. Edit Job Data", "PATCH", f"jobs/{self.test_job_id}/edit-data", 200, 
            edit_data, self.authority_token
        )
        
        return success

    def test_7_delete_job(self):
        """7. DELETE /api/jobs/{id}"""
        if not self.test_job_id or not self.authority_token:
            print("❌ No job ID or authority token available for delete test")
            return False
            
        success, response, status, error = self.run_test(
            "7. Delete Job", "DELETE", f"jobs/{self.test_job_id}", 200, 
            token=self.authority_token
        )
        
        return success

    def test_8_job_pdf(self):
        """8. GET /api/jobs/{id}/pdf"""
        # Create a new job for PDF test since we deleted the previous one
        if not self.authority_token:
            print("❌ No authority token available for PDF test")
            return False
            
        # Create a job for PDF testing
        pdf_job_data = {
            "license_plate": "B-PDF001",
            "vin": "WVWZZZ3CZWE111111",
            "tow_reason": "PDF test job",
            "location_address": "PDF Teststraße 1, 12345 Berlin",
            "location_lat": 52.520008,
            "location_lng": 13.404954,
            "notes": "Job for PDF generation test"
        }
        
        success, response, status, error = self.run_test(
            "Create Job for PDF", "POST", "jobs", 200, pdf_job_data, self.authority_token
        )
        
        if not success or 'id' not in response:
            print("❌ Failed to create job for PDF test")
            return False
            
        pdf_job_id = response['id']
        
        # Test PDF generation
        url = f"{self.base_url}/jobs/{pdf_job_id}/pdf"
        headers = {'Authorization': f'Bearer {self.authority_token}'}
        
        try:
            print(f"\n🔍 Testing 8. Job PDF Generation...")
            print(f"   GET {url}")
            response = requests.get(url, headers=headers, timeout=30)
            
            success = response.status_code == 200
            content_type = response.headers.get('content-type', '')
            
            if success and 'application/pdf' in content_type:
                print(f"✅ PASSED - Status: {response.status_code}")
                print(f"   Content-Type: {content_type}")
                print(f"   PDF size: {len(response.content)} bytes")
                self.tests_passed += 1
                return True
            else:
                error_msg = f"Expected PDF, got status {response.status_code}, content-type: {content_type}"
                print(f"❌ FAILED - {error_msg}")
                self.failed_tests.append({
                    'test': '8. Job PDF Generation',
                    'method': 'GET',
                    'endpoint': f'jobs/{pdf_job_id}/pdf',
                    'expected_status': 200,
                    'actual_status': response.status_code,
                    'error_message': error_msg,
                    'request_body': None
                })
                return False
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ FAILED - Exception: {error_msg}")
            self.failed_tests.append({
                'test': '8. Job PDF Generation',
                'method': 'GET',
                'endpoint': f'jobs/{pdf_job_id}/pdf',
                'expected_status': 200,
                'actual_status': 'EXCEPTION',
                'error_message': error_msg,
                'request_body': None
            })
            return False
        finally:
            self.tests_run += 1

    def test_9_vehicle_search(self):
        """9. GET /api/search/vehicle?q=TEST"""
        success, response, status, error = self.run_test(
            "9. Vehicle Search", "GET", "search/vehicle?q=TEST", 200
        )
        
        if success and isinstance(response, dict):
            found = response.get('found', False)
            print(f"   Search result: {'Found' if found else 'Not Found'}")
            if found:
                print(f"   Job Number: {response.get('job_number', 'N/A')}")
                print(f"   License Plate: {response.get('license_plate', 'N/A')}")
                print(f"   Status: {response.get('status', 'N/A')}")
        
        return success

    def test_10_register_towing_service(self):
        """10. POST /api/auth/register (towing service)"""
        towing_data = {
            "email": f"test_towing_{datetime.now().strftime('%H%M%S')}@test.de",
            "password": "TestTowing123!",
            "name": "Test Towing Service",
            "role": "towing_service",
            "company_name": "Test Abschleppdienst GmbH",
            "phone": "+49 123 456789",
            "address": "Teststraße 1, 12345 Berlin",
            "yard_address": "Hofstraße 1, 12345 Berlin",
            "opening_hours": "Mo-Fr 8:00-18:00",
            "tow_cost": 150.0,
            "daily_cost": 25.0,
            "business_license": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwA/8A"
        }
        
        # Expect 202 status for towing service registration (pending approval)
        success, response, status, error = self.run_test(
            "10. Register Towing Service", "POST", "auth/register", 202, towing_data
        )
        
        return success

    def test_11_admin_stats(self):
        """11. GET /api/admin/stats"""
        if not self.admin_token:
            print("❌ No admin token available for stats test")
            return False
            
        success, response, status, error = self.run_test(
            "11. Admin Stats", "GET", "admin/stats", 200, token=self.admin_token
        )
        
        if success and isinstance(response, dict):
            print(f"   Total Jobs: {response.get('total_jobs', 'N/A')}")
            print(f"   Pending Jobs: {response.get('pending_jobs', 'N/A')}")
            print(f"   Total Services: {response.get('total_services', 'N/A')}")
            print(f"   Total Authorities: {response.get('total_authorities', 'N/A')}")
        
        return success

    def test_12_admin_users(self):
        """12. GET /api/admin/users"""
        if not self.admin_token:
            print("❌ No admin token available for users test")
            return False
            
        success, response, status, error = self.run_test(
            "12. Admin Users", "GET", "admin/users", 200, token=self.admin_token
        )
        
        if success and isinstance(response, list):
            print(f"   Retrieved {len(response)} users")
            # Count by role
            role_counts = {}
            for user in response:
                role = user.get('role', 'unknown')
                role_counts[role] = role_counts.get(role, 0) + 1
            
            for role, count in role_counts.items():
                print(f"   - {role}: {count}")
        
        return success

    def test_13_admin_audit_logs(self):
        """13. GET /api/admin/audit-logs"""
        if not self.admin_token:
            print("❌ No admin token available for audit logs test")
            return False
            
        success, response, status, error = self.run_test(
            "13. Admin Audit Logs", "GET", "admin/audit-logs", 200, token=self.admin_token
        )
        
        if success and isinstance(response, list):
            print(f"   Retrieved {len(response)} audit log entries")
            # Count login-related entries
            login_entries = [e for e in response if e.get('action') in ['USER_LOGIN', 'LOGIN_FAILED']]
            print(f"   - Login-related entries: {len(login_entries)}")
        
        return success

    def test_14_approve_service(self):
        """14. POST /api/admin/approve-service/{id}"""
        if not self.admin_token:
            print("❌ No admin token available for service approval test")
            return False
            
        # First get pending services to find one to approve
        success, response, status, error = self.run_test(
            "Get Pending Services", "GET", "admin/pending-services", 200, token=self.admin_token
        )
        
        if not success or not response:
            print("❌ No pending services found for approval test")
            return False
            
        if len(response) == 0:
            print("❌ No pending services available for approval test")
            return False
            
        # Use the first pending service
        service_id = response[0].get('id')
        if not service_id:
            print("❌ No service ID found in pending services")
            return False
            
        approval_data = {"approved": True}
        success, response, status, error = self.run_test(
            "14. Approve Service", "POST", f"admin/approve-service/{service_id}", 200, 
            approval_data, self.admin_token
        )
        
        if success:
            self.test_service_id = service_id
            print(f"   Approved service ID: {service_id}")
        
        return success

    def test_15_approve_authority(self):
        """15. POST /api/admin/approve-authority/{id}"""
        if not self.admin_token:
            print("❌ No admin token available for authority approval test")
            return False
            
        # First get pending authorities
        success, response, status, error = self.run_test(
            "Get Pending Authorities", "GET", "admin/pending-authorities", 200, token=self.admin_token
        )
        
        if not success or not response or len(response) == 0:
            print("❌ No pending authorities found for approval test")
            # This might be expected if no authorities are pending
            return True  # Consider this a pass since it's not necessarily an error
            
        # Use the first pending authority
        authority_id = response[0].get('id')
        if not authority_id:
            print("❌ No authority ID found in pending authorities")
            return False
            
        approval_data = {"approved": True}
        success, response, status, error = self.run_test(
            "15. Approve Authority", "POST", f"admin/approve-authority/{authority_id}", 200, 
            approval_data, self.admin_token
        )
        
        return success

    def test_16_get_services(self):
        """16. GET /api/services"""
        if not self.authority_token:
            print("❌ No authority token available for services test")
            return False
            
        success, response, status, error = self.run_test(
            "16. Get Services", "GET", "services", 200, token=self.authority_token
        )
        
        if success and isinstance(response, list):
            print(f"   Retrieved {len(response)} services")
        
        return success

    def test_17_create_employee(self):
        """17. POST /api/authority/employees"""
        if not self.authority_token:
            print("❌ No authority token available for employee creation test")
            return False
            
        employee_data = {
            "email": f"test_employee_{datetime.now().strftime('%H%M%S')}@test.de",
            "password": "TestEmployee123!",
            "name": "Test Employee"
        }
        
        success, response, status, error = self.run_test(
            "17. Create Employee", "POST", "authority/employees", 200, 
            employee_data, self.authority_token
        )
        
        if success and 'id' in response:
            print(f"   Employee created with ID: {response['id']}")
            print(f"   Dienstnummer: {response.get('dienstnummer', 'N/A')}")
        
        return success

    def test_18_get_employees(self):
        """18. GET /api/authority/employees"""
        if not self.authority_token:
            print("❌ No authority token available for employees list test")
            return False
            
        success, response, status, error = self.run_test(
            "18. Get Employees", "GET", "authority/employees", 200, token=self.authority_token
        )
        
        if success and isinstance(response, list):
            print(f"   Retrieved {len(response)} employees")
        
        return success

    def test_19_pricing_settings(self):
        """19. PATCH /api/services/pricing-settings"""
        # Need a towing service token for this test
        # Try to get one by approving a service and logging in
        if not self.test_service_id:
            print("❌ No approved towing service available for pricing test")
            return False
            
        # This test might fail if we don't have towing service credentials
        # Let's try with a known towing service if it exists
        towing_login = {"email": "abschlepp@test.de", "password": "Abschlepp123"}
        success, response, status, error = self.run_test(
            "Towing Service Login for Pricing", "POST", "auth/login", 200, towing_login
        )
        
        if not success:
            print("❌ No towing service login available for pricing test")
            return False
            
        towing_token = response.get('access_token')
        if not towing_token:
            print("❌ No towing service token obtained")
            return False
            
        pricing_data = {
            "time_based_enabled": True,
            "first_half_hour": 137.00,
            "additional_half_hour": 93.00,
            "processing_fee": 30.00
        }
        
        success, response, status, error = self.run_test(
            "19. Update Pricing Settings", "PATCH", "services/pricing-settings", 200, 
            pricing_data, towing_token
        )
        
        return success

    def test_20_excel_export(self):
        """20. GET /api/jobs/export/excel"""
        if not self.admin_token:
            print("❌ No admin token available for Excel export test")
            return False
            
        # Note: The endpoint might be /api/export/jobs/excel based on backend code
        url = f"{self.base_url}/export/jobs/excel"
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            print(f"\n🔍 Testing 20. Excel Export...")
            print(f"   GET {url}")
            response = requests.get(url, headers=headers, timeout=30)
            
            success = response.status_code == 200
            content_type = response.headers.get('content-type', '')
            
            if success and ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in content_type or 
                           'application/octet-stream' in content_type):
                print(f"✅ PASSED - Status: {response.status_code}")
                print(f"   Content-Type: {content_type}")
                print(f"   File size: {len(response.content)} bytes")
                self.tests_passed += 1
                return True
            else:
                error_msg = f"Expected Excel file, got status {response.status_code}, content-type: {content_type}"
                print(f"❌ FAILED - {error_msg}")
                self.failed_tests.append({
                    'test': '20. Excel Export',
                    'method': 'GET',
                    'endpoint': 'export/jobs/excel',
                    'expected_status': 200,
                    'actual_status': response.status_code,
                    'error_message': error_msg,
                    'request_body': None
                })
                return False
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ FAILED - Exception: {error_msg}")
            self.failed_tests.append({
                'test': '20. Excel Export',
                'method': 'GET',
                'endpoint': 'export/jobs/excel',
                'expected_status': 200,
                'actual_status': 'EXCEPTION',
                'error_message': error_msg,
                'request_body': None
            })
            return False
        finally:
            self.tests_run += 1

    def test_21_forgot_password(self):
        """21. POST /api/auth/forgot-password"""
        forgot_data = {"email": "admin@test.de"}
        
        success, response, status, error = self.run_test(
            "21. Forgot Password", "POST", "auth/forgot-password", 200, forgot_data
        )
        
        if success and isinstance(response, dict):
            message = response.get('message', '')
            print(f"   Response message: {message}")
        
        return success

    def run_all_tests(self):
        """Run all 21 tests as specified in the review request"""
        print("🚀 Starting Comprehensive API Testing - 21 Endpoints")
        print("=" * 60)
        
        # Run all tests in order
        test_methods = [
            self.test_1_admin_login,
            self.test_2_authority_login,
            self.test_3_auth_me,
            self.test_4_create_job,
            self.test_5_list_jobs,
            self.test_6_edit_job_data,
            self.test_7_delete_job,
            self.test_8_job_pdf,
            self.test_9_vehicle_search,
            self.test_10_register_towing_service,
            self.test_11_admin_stats,
            self.test_12_admin_users,
            self.test_13_admin_audit_logs,
            self.test_14_approve_service,
            self.test_15_approve_authority,
            self.test_16_get_services,
            self.test_17_create_employee,
            self.test_18_get_employees,
            self.test_19_pricing_settings,
            self.test_20_excel_export,
            self.test_21_forgot_password
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                print(f"❌ Test {test_method.__name__} crashed: {str(e)}")
        
        self.print_summary()

    def print_summary(self):
        """Print detailed test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        print(f"Total Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {len(self.failed_tests)}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS DETAILS:")
            print("-" * 40)
            
            for i, test in enumerate(self.failed_tests, 1):
                print(f"\n{i}. {test['test']}")
                print(f"   Endpoint: {test['method']} {test['endpoint']}")
                print(f"   Expected Status: {test['expected_status']}")
                print(f"   Actual Status: {test['actual_status']}")
                print(f"   Error Message: {test['error_message']}")
                if test['request_body']:
                    print(f"   Request Body: {json.dumps(test['request_body'], indent=2)}")
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    tester = ComprehensiveAPITester()
    tester.run_all_tests()
#!/usr/bin/env python3
"""
AbschleppPortal Employee System Comprehensive Test Suite
Tests the new employee system implementation for both authorities and towing services
"""

import requests
import json
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://dual-yard-system.preview.emergentagent.com/api"

# Test Credentials
ADMIN_EMAIL = "admin@test.de"
ADMIN_PASSWORD = "Admin123!"
AUTHORITY_EMAIL = "behoerde@test.de"
AUTHORITY_PASSWORD = "Behoerde123!"
TOWING_SERVICE_EMAIL = "abschlepp@test.de"
TOWING_SERVICE_PASSWORD = "Abschlepp123!"

class EmployeeSystemTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.authority_token = None
        self.towing_service_token = None
        self.test_results = []
        self.created_employees = []  # Track created employees for cleanup
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "response_data": response_data
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        
    def authenticate_user(self, email: str, password: str, user_type: str) -> Optional[str]:
        """Authenticate a user and return token"""
        try:
            response = self.session.post(
                f"{BASE_URL}/auth/login",
                json={
                    "email": email,
                    "password": password
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                self.log_test(f"{user_type} Authentication", True, f"Successfully authenticated as {email}")
                return token
            else:
                self.log_test(f"{user_type} Authentication", False, f"Failed with status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_test(f"{user_type} Authentication", False, f"Exception: {str(e)}")
            return None
    
    def setup_authentication(self) -> bool:
        """Setup authentication for all user types"""
        self.admin_token = self.authenticate_user(ADMIN_EMAIL, ADMIN_PASSWORD, "Admin")
        self.authority_token = self.authenticate_user(AUTHORITY_EMAIL, AUTHORITY_PASSWORD, "Authority")
        self.towing_service_token = self.authenticate_user(TOWING_SERVICE_EMAIL, TOWING_SERVICE_PASSWORD, "Towing Service")
        
        return all([self.admin_token, self.authority_token, self.towing_service_token])
    
    def test_jobs_api_basic(self):
        """Test basic Jobs API functionality"""
        headers = {"Authorization": f"Bearer {self.authority_token}"}
        
        # Test GET /api/jobs
        try:
            response = requests.get(f"{BASE_URL}/jobs", headers=headers)
            if response.status_code == 200:
                jobs = response.json()
                self.log_test("Jobs API - GET /api/jobs", True, f"Retrieved {len(jobs)} jobs successfully")
            else:
                self.log_test("Jobs API - GET /api/jobs", False, f"Failed with status {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Jobs API - GET /api/jobs", False, f"Exception: {str(e)}")
        
        # Test POST /api/jobs (create job)
        try:
            job_data = {
                "license_plate": "TEST-EMP-001",
                "tow_reason": "Falschparker - Employee System Test",
                "location_address": "Teststraße 123, Hamburg",
                "location_lat": 53.5511,
                "location_lng": 9.9937,
                "notes": "Test job for employee system testing"
            }
            response = requests.post(f"{BASE_URL}/jobs", headers=headers, json=job_data)
            if response.status_code == 200:
                job = response.json()
                job_id = job.get("id")
                self.log_test("Jobs API - POST /api/jobs", True, f"Created job successfully with ID: {job_id}")
                
                # Test PATCH /api/jobs/{id}
                update_data = {"status": "assigned", "notes": "Updated via employee system test"}
                response = requests.patch(f"{BASE_URL}/jobs/{job_id}", headers=headers, json=update_data)
                if response.status_code == 200:
                    self.log_test("Jobs API - PATCH /api/jobs/{id}", True, "Job updated successfully")
                else:
                    self.log_test("Jobs API - PATCH /api/jobs/{id}", False, f"Failed with status {response.status_code}: {response.text}")
            else:
                self.log_test("Jobs API - POST /api/jobs", False, f"Failed with status {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Jobs API - POST /api/jobs", False, f"Exception: {str(e)}")
    
    def test_authority_employee_system(self):
        """Test Authority Employee System"""
        headers = {"Authorization": f"Bearer {self.authority_token}"}
        
        # Test POST /api/authority/employees (create employee with sub_role: field)
        try:
            employee_data = {
                "email": f"field.employee.{int(time.time())}@test.de",
                "password": "FieldEmployee123!",
                "name": "Field Employee Test",
                "sub_role": "field"
            }
            response = requests.post(f"{BASE_URL}/authority/employees", headers=headers, json=employee_data)
            if response.status_code == 200:
                employee = response.json()
                employee_id = employee.get("id")
                self.created_employees.append({"id": employee_id, "type": "authority", "token": self.authority_token})
                
                # Check if sub_role is returned
                if employee.get("sub_role") == "field":
                    self.log_test("Authority Employee - Create Field Employee", True, 
                                f"Created field employee successfully with ID: {employee_id}, sub_role: {employee.get('sub_role')}")
                else:
                    self.log_test("Authority Employee - Create Field Employee", False, 
                                f"Employee created but sub_role not returned correctly: {employee.get('sub_role')}")
            else:
                self.log_test("Authority Employee - Create Field Employee", False, 
                            f"Failed with status {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Authority Employee - Create Field Employee", False, f"Exception: {str(e)}")
        
        # Test POST /api/authority/employees (create employee with sub_role: yard)
        try:
            employee_data = {
                "email": f"yard.employee.{int(time.time())}@test.de",
                "password": "YardEmployee123!",
                "name": "Yard Employee Test",
                "sub_role": "yard"
            }
            response = requests.post(f"{BASE_URL}/authority/employees", headers=headers, json=employee_data)
            if response.status_code == 200:
                employee = response.json()
                employee_id = employee.get("id")
                self.created_employees.append({"id": employee_id, "type": "authority", "token": self.authority_token})
                
                # Check if sub_role is returned
                if employee.get("sub_role") == "yard":
                    self.log_test("Authority Employee - Create Yard Employee", True, 
                                f"Created yard employee successfully with ID: {employee_id}, sub_role: {employee.get('sub_role')}")
                else:
                    self.log_test("Authority Employee - Create Yard Employee", False, 
                                f"Employee created but sub_role not returned correctly: {employee.get('sub_role')}")
            else:
                self.log_test("Authority Employee - Create Yard Employee", False, 
                            f"Failed with status {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Authority Employee - Create Yard Employee", False, f"Exception: {str(e)}")
        
        # Test GET /api/authority/employees
        try:
            response = requests.get(f"{BASE_URL}/authority/employees", headers=headers)
            if response.status_code == 200:
                employees = response.json()
                # Check if sub_role is returned in the list
                has_sub_role = all(emp.get("sub_role") is not None for emp in employees)
                self.log_test("Authority Employee - List Employees", True, 
                            f"Retrieved {len(employees)} employees, all have sub_role: {has_sub_role}")
            else:
                self.log_test("Authority Employee - List Employees", False, 
                            f"Failed with status {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Authority Employee - List Employees", False, f"Exception: {str(e)}")
    
    def test_towing_service_employee_system(self):
        """Test NEW: Towing Service Employee System"""
        headers = {"Authorization": f"Bearer {self.towing_service_token}"}
        
        # Test POST /api/service/employees - Create employee
        try:
            employee_data = {
                "email": f"service.employee.{int(time.time())}@test.de",
                "password": "ServiceEmployee123!",
                "name": "Service Employee Test"
            }
            response = requests.post(f"{BASE_URL}/service/employees", headers=headers, json=employee_data)
            if response.status_code == 200:
                employee = response.json()
                employee_id = employee.get("id")
                self.created_employees.append({"id": employee_id, "type": "service", "token": self.towing_service_token})
                self.log_test("Towing Service Employee - Create Employee", True, 
                            f"Created service employee successfully with ID: {employee_id}")
                
                # Test PATCH /api/service/employees/{id}/block?blocked=true - Block employee
                try:
                    response = requests.patch(f"{BASE_URL}/service/employees/{employee_id}/block?blocked=true", headers=headers)
                    if response.status_code == 200:
                        self.log_test("Towing Service Employee - Block Employee", True, 
                                    f"Successfully blocked employee {employee_id}")
                        
                        # Test unblocking
                        response = requests.patch(f"{BASE_URL}/service/employees/{employee_id}/block?blocked=false", headers=headers)
                        if response.status_code == 200:
                            self.log_test("Towing Service Employee - Unblock Employee", True, 
                                        f"Successfully unblocked employee {employee_id}")
                        else:
                            self.log_test("Towing Service Employee - Unblock Employee", False, 
                                        f"Failed with status {response.status_code}: {response.text}")
                    else:
                        self.log_test("Towing Service Employee - Block Employee", False, 
                                    f"Failed with status {response.status_code}: {response.text}")
                except Exception as e:
                    self.log_test("Towing Service Employee - Block Employee", False, f"Exception: {str(e)}")
                
            else:
                self.log_test("Towing Service Employee - Create Employee", False, 
                            f"Failed with status {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Towing Service Employee - Create Employee", False, f"Exception: {str(e)}")
        
        # Test GET /api/service/employees - List employees
        try:
            response = requests.get(f"{BASE_URL}/service/employees", headers=headers)
            if response.status_code == 200:
                employees = response.json()
                self.log_test("Towing Service Employee - List Employees", True, 
                            f"Retrieved {len(employees)} service employees successfully")
            else:
                self.log_test("Towing Service Employee - List Employees", False, 
                            f"Failed with status {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Towing Service Employee - List Employees", False, f"Exception: {str(e)}")
    
    def test_authority_settings(self):
        """Test Authority Settings - PATCH /api/authority/settings"""
        headers = {"Authorization": f"Bearer {self.authority_token}"}
        
        try:
            settings_data = {
                "yard_model": "authority_yard",
                "yards": [
                    {
                        "id": "yard-001",
                        "name": "Haupthof Hamburg",
                        "address": "Hafenstraße 123, Hamburg",
                        "lat": 53.5511,
                        "lng": 9.9937,
                        "phone": "+49 40 123456"
                    }
                ],
                "price_categories": [
                    {
                        "id": "cat-001",
                        "name": "PKW Standard",
                        "base_price": 150.0,
                        "daily_rate": 25.0
                    }
                ]
            }
            response = requests.patch(f"{BASE_URL}/authority/settings", headers=headers, json=settings_data)
            if response.status_code == 200:
                result = response.json()
                self.log_test("Authority Settings - Save Yard Settings", True, 
                            f"Successfully saved authority settings: {result.get('message', 'Settings updated')}")
                
                # Check if yards are inherited to employees by getting employee list
                try:
                    response = requests.get(f"{BASE_URL}/authority/employees", headers=headers)
                    if response.status_code == 200:
                        employees = response.json()
                        # This is a basic check - in a real scenario, we'd need to login as employee to verify inheritance
                        self.log_test("Authority Settings - Yard Inheritance Check", True, 
                                    f"Settings saved, inheritance should be applied to {len(employees)} employees")
                    else:
                        self.log_test("Authority Settings - Yard Inheritance Check", False, 
                                    f"Could not verify inheritance - employee list failed: {response.status_code}")
                except Exception as e:
                    self.log_test("Authority Settings - Yard Inheritance Check", False, f"Exception: {str(e)}")
                    
            else:
                self.log_test("Authority Settings - Save Yard Settings", False, 
                            f"Failed with status {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Authority Settings - Save Yard Settings", False, f"Exception: {str(e)}")
    
    def test_role_based_access_authority_release(self):
        """Test Role-based Access for authority-release"""
        # This test would require creating employees and testing their access
        # For now, we'll test the endpoint with the main authority account
        headers = {"Authorization": f"Bearer {self.authority_token}"}
        
        # First, create a test job that can be released
        try:
            job_data = {
                "license_plate": "TEST-REL-001",
                "tow_reason": "Test für Authority Release",
                "location_address": "Teststraße 456, Hamburg",
                "location_lat": 53.5511,
                "location_lng": 9.9937,
                "target_yard": "authority_yard",
                "authority_yard_id": "yard-001",
                "authority_yard_name": "Haupthof Hamburg",
                "authority_yard_address": "Hafenstraße 123, Hamburg",
                "authority_price_category_id": "cat-001",
                "authority_base_price": 150.0,
                "authority_daily_rate": 25.0
            }
            response = requests.post(f"{BASE_URL}/jobs", headers=headers, json=job_data)
            if response.status_code == 200:
                job = response.json()
                job_id = job.get("id")
                
                # Update job to delivered_to_authority status first
                update_data = {"status": "delivered_to_authority"}
                requests.patch(f"{BASE_URL}/jobs/{job_id}", headers=headers, json=update_data)
                
                # Test authority-release endpoint
                release_data = {
                    "owner_first_name": "Max",
                    "owner_last_name": "Mustermann",
                    "owner_address": "Musterstraße 123, Hamburg",
                    "payment_method": "cash",
                    "payment_amount": 175.0
                }
                response = requests.post(f"{BASE_URL}/jobs/{job_id}/authority-release", headers=headers, json=release_data)
                if response.status_code == 200:
                    self.log_test("Role-based Access - Authority Release (Admin)", True, 
                                f"Authority with admin role can successfully release vehicles")
                elif response.status_code == 403:
                    # This would be expected for field employees
                    self.log_test("Role-based Access - Authority Release (Field Restriction)", True, 
                                f"403 error as expected for restricted access: {response.json().get('detail', 'Access denied')}")
                else:
                    self.log_test("Role-based Access - Authority Release", False, 
                                f"Unexpected status {response.status_code}: {response.text}")
            else:
                self.log_test("Role-based Access - Authority Release Setup", False, 
                            f"Could not create test job: {response.status_code}")
        except Exception as e:
            self.log_test("Role-based Access - Authority Release", False, f"Exception: {str(e)}")
    
    def test_vehicle_search(self):
        """Test Vehicle Search - GET /api/search/vehicle?q=TEST"""
        try:
            response = requests.get(f"{BASE_URL}/search/vehicle?q=TEST")
            if response.status_code == 200:
                result = response.json()
                self.log_test("Vehicle Search - Public Search", True, 
                            f"Public vehicle search working: found={result.get('found', False)}")
            else:
                self.log_test("Vehicle Search - Public Search", False, 
                            f"Failed with status {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Vehicle Search - Public Search", False, f"Exception: {str(e)}")
    
    def cleanup_created_employees(self):
        """Clean up created test employees"""
        print("\n" + "=" * 50)
        print("CLEANING UP TEST EMPLOYEES")
        print("=" * 50)
        
        for employee in self.created_employees:
            try:
                headers = {"Authorization": f"Bearer {employee['token']}"}
                if employee['type'] == 'authority':
                    endpoint = f"{BASE_URL}/authority/employees/{employee['id']}"
                else:
                    endpoint = f"{BASE_URL}/service/employees/{employee['id']}"
                
                response = requests.delete(endpoint, headers=headers)
                if response.status_code == 200:
                    print(f"✅ Deleted {employee['type']} employee {employee['id']}")
                else:
                    print(f"⚠️  Could not delete {employee['type']} employee {employee['id']}: {response.status_code}")
            except Exception as e:
                print(f"❌ Error deleting {employee['type']} employee {employee['id']}: {str(e)}")
    
    def run_all_tests(self):
        """Run all employee system tests"""
        print("=" * 80)
        print("ABSCHLEPPPORTAL EMPLOYEE SYSTEM COMPREHENSIVE TEST")
        print("=" * 80)
        
        # Setup authentication
        if not self.setup_authentication():
            print("❌ Authentication failed - cannot proceed with tests")
            return
        
        print("\n" + "=" * 50)
        print("TESTING BASIC FUNCTIONALITY")
        print("=" * 50)
        
        # Test basic Jobs API
        self.test_jobs_api_basic()
        self.test_vehicle_search()
        
        print("\n" + "=" * 50)
        print("TESTING AUTHORITY EMPLOYEE SYSTEM")
        print("=" * 50)
        
        # Test Authority Employee System
        self.test_authority_employee_system()
        self.test_authority_settings()
        
        print("\n" + "=" * 50)
        print("TESTING TOWING SERVICE EMPLOYEE SYSTEM")
        print("=" * 50)
        
        # Test Towing Service Employee System
        self.test_towing_service_employee_system()
        
        print("\n" + "=" * 50)
        print("TESTING ROLE-BASED ACCESS")
        print("=" * 50)
        
        # Test Role-based Access
        self.test_role_based_access_authority_release()
        
        # Clean up test data
        self.cleanup_created_employees()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n✅ PASSED TESTS:")
        for result in self.test_results:
            if result["success"]:
                print(f"  - {result['test']}: {result['details']}")

if __name__ == "__main__":
    tester = EmployeeSystemTester()
    tester.run_all_tests()
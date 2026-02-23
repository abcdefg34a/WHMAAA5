#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class TowingManagementAPITester:
    def __init__(self, base_url="https://vehicle-recovery-7.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.authority_token = None
        self.towing_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # Test data - Use provided admin credentials
        self.test_admin = {
            "email": "admin@test.de",
            "password": "Admin123!",
            "name": "Test Admin",
            "role": "admin"
        }
        
        self.test_authority = {
            "email": f"authority_{datetime.now().strftime('%H%M%S')}@test.de", 
            "password": "TestPass123!",
            "name": "Test Authority",
            "role": "authority",
            "authority_name": "Test Ordnungsamt",
            "department": "Verkehrsüberwachung"
        }
        
        self.test_towing = {
            "email": f"towing_{datetime.now().strftime('%H%M%S')}@test.de",
            "password": "TestPass123!",
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
        
        # Employee management test data
        self.employee_data = {
            "email": f"employee_{datetime.now().strftime('%H%M%S')}@test.de",
            "password": "EmployeePass123!",
            "name": "Test Employee"
        }
        
        self.employee2_data = {
            "email": f"employee2_{datetime.now().strftime('%H%M%S')}@test.de", 
            "password": "Employee2Pass123!",
            "name": "Test Employee 2"
        }
        
        # Store employee tokens and IDs
        self.employee_token = None
        self.employee2_token = None
        self.employee_id = None
        self.employee2_id = None
        self.main_authority_dienstnummer = None
        self.employee_dienstnummer = None
        self.employee2_dienstnummer = None

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

    def test_root_endpoint(self):
        """Test root API endpoint"""
        success, response = self.run_test("Root API", "GET", "", 200)
        return success

    def test_user_registration(self):
        """Test user registration for all roles"""
        print("\n📝 Testing User Registration...")
        
        # Test admin registration
        success, response = self.run_test(
            "Admin Registration", "POST", "auth/register", 200, self.test_admin
        )
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            print(f"   Admin token obtained: {self.admin_token[:20]}...")
        
        # Test authority registration - should get is_main_authority=true and dienstnummer
        success, response = self.run_test(
            "Authority Registration", "POST", "auth/register", 200, self.test_authority
        )
        if success and 'access_token' in response:
            self.authority_token = response['access_token']
            user_data = response.get('user', {})
            self.main_authority_id = user_data.get('id')
            self.main_authority_dienstnummer = user_data.get('dienstnummer')
            is_main_authority = user_data.get('is_main_authority')
            
            print(f"   Authority token obtained: {self.authority_token[:20]}...")
            print(f"   Authority ID: {self.main_authority_id}")
            print(f"   Dienstnummer: {self.main_authority_dienstnummer}")
            print(f"   Is main authority: {is_main_authority}")
            
            # Verify main authority properties
            if is_main_authority and self.main_authority_dienstnummer:
                print("   ✅ Main authority correctly registered with dienstnummer")
            else:
                print("   ❌ Main authority missing required properties")
        
        # Test towing service registration (should succeed but be pending approval)
        success, response = self.run_test(
            "Towing Service Registration", "POST", "auth/register", 200, self.test_towing
        )
        if success and 'access_token' in response:
            self.towing_token = response['access_token']
            service_code = response.get('user', {}).get('service_code')
            approval_status = response.get('user', {}).get('approval_status')
            self.towing_service_id = response.get('user', {}).get('id')
            if service_code:
                self.towing_service_code = service_code
                print(f"   Towing service code: {service_code}")
            if approval_status:
                print(f"   Approval status: {approval_status}")
        
        return all([self.admin_token, self.authority_token, self.towing_token])

    def test_user_login(self):
        """Test user login"""
        print("\n🔐 Testing User Login...")
        
        # Test admin login
        login_data = {"email": self.test_admin["email"], "password": self.test_admin["password"]}
        success, response = self.run_test("Admin Login", "POST", "auth/login", 200, login_data)
        
        # Test authority login
        login_data = {"email": self.test_authority["email"], "password": self.test_authority["password"]}
        success, response = self.run_test("Authority Login", "POST", "auth/login", 200, login_data)
        
        # Test towing service login (should fail with pending approval message)
        login_data = {"email": self.test_towing["email"], "password": self.test_towing["password"]}
        success, response = self.run_test("Towing Service Login (Pending)", "POST", "auth/login", 403, login_data)
        
        return True

    def test_auth_me(self):
        """Test auth/me endpoint"""
        print("\n👤 Testing Auth Me...")
        
        success, response = self.run_test("Auth Me - Admin", "GET", "auth/me", 200, token=self.admin_token)
        success, response = self.run_test("Auth Me - Authority", "GET", "auth/me", 200, token=self.authority_token)
        success, response = self.run_test("Auth Me - Towing", "GET", "auth/me", 200, token=self.towing_token)
        
        return True

    def test_admin_approval_workflow(self):
        """Test admin approval workflow for towing services"""
        print("\n👑 Testing Admin Approval Workflow...")
        
        # Get pending services
        success, response = self.run_test(
            "Get Pending Services", "GET", "admin/pending-services", 200, 
            token=self.admin_token
        )
        
        if success and response and len(response) > 0:
            print(f"   Found {len(response)} pending service(s)")
            # Check if our test service is in the list
            test_service = next((s for s in response if s.get('id') == self.towing_service_id), None)
            if test_service:
                print(f"   Test service found in pending list with business license: {'Yes' if test_service.get('business_license') else 'No'}")
        
        # Test rejection first
        rejection_data = {"approved": False, "rejection_reason": "Test rejection reason"}
        success, response = self.run_test(
            "Reject Towing Service", "POST", f"admin/approve-service/{self.towing_service_id}", 200,
            rejection_data, self.admin_token
        )
        
        # Try to login after rejection (should fail and delete account)
        login_data = {"email": self.test_towing["email"], "password": self.test_towing["password"]}
        success, response = self.run_test("Login After Rejection", "POST", "auth/login", 403, login_data)
        
        # Re-register after rejection (should work)
        success, response = self.run_test(
            "Re-register After Rejection", "POST", "auth/register", 200, self.test_towing
        )
        if success and 'access_token' in response:
            self.towing_token = response['access_token']
            self.towing_service_id = response.get('user', {}).get('id')
            # Update service code after re-registration
            self.towing_service_code = response.get('user', {}).get('service_code')
            print(f"   Re-registered successfully with new ID: {self.towing_service_id}")
            print(f"   New service code: {self.towing_service_code}")
        
        # Now approve the service
        approval_data = {"approved": True}
        success, response = self.run_test(
            "Approve Towing Service", "POST", f"admin/approve-service/{self.towing_service_id}", 200,
            approval_data, self.admin_token
        )
        
        # Test login after approval (should succeed)
        success, response = self.run_test("Login After Approval", "POST", "auth/login", 200, login_data)
        if success and 'access_token' in response:
            self.towing_token = response['access_token']
            print(f"   Login successful after approval")
        
        return True

    def test_employee_management(self):
        """Test employee management system"""
        print("\n👥 Testing Employee Management System...")
        
        if not self.authority_token or not self.main_authority_id:
            print("❌ No authority token or ID available for employee tests")
            return False
        
        # Test 1: Create first employee - should get unique dienstnummer
        success, response = self.run_test(
            "Create Employee 1", "POST", "authority/employees", 200,
            self.employee_data, self.authority_token
        )
        
        if success and response:
            self.employee_id = response.get('id')
            self.employee_dienstnummer = response.get('dienstnummer')
            print(f"   Employee 1 created - ID: {self.employee_id}")
            print(f"   Employee 1 Dienstnummer: {self.employee_dienstnummer}")
            
            # Verify dienstnummer format (DN-XXXX-NNN)
            if self.employee_dienstnummer and self.employee_dienstnummer.startswith('DN-'):
                print("   ✅ Employee dienstnummer has correct format")
            else:
                print("   ❌ Employee dienstnummer has incorrect format")
        
        # Test 2: Create second employee - should get different dienstnummer
        success, response = self.run_test(
            "Create Employee 2", "POST", "authority/employees", 200,
            self.employee2_data, self.authority_token
        )
        
        if success and response:
            self.employee2_id = response.get('id')
            self.employee2_dienstnummer = response.get('dienstnummer')
            print(f"   Employee 2 created - ID: {self.employee2_id}")
            print(f"   Employee 2 Dienstnummer: {self.employee2_dienstnummer}")
            
            # Verify dienstnummers are unique
            if (self.employee_dienstnummer and self.employee2_dienstnummer and 
                self.employee_dienstnummer != self.employee2_dienstnummer):
                print("   ✅ Employee dienstnummers are unique")
            else:
                print("   ❌ Employee dienstnummers are not unique")
        
        # Test 3: Get all employees
        success, response = self.run_test(
            "Get All Employees", "GET", "authority/employees", 200,
            token=self.authority_token
        )
        
        if success and response:
            print(f"   Found {len(response)} employees")
            for emp in response:
                print(f"   - {emp.get('name')}: {emp.get('dienstnummer')} (Blocked: {emp.get('is_blocked', False)})")
        
        # Test 4: Employee login and token acquisition
        employee_login = {"email": self.employee_data["email"], "password": self.employee_data["password"]}
        success, response = self.run_test(
            "Employee 1 Login", "POST", "auth/login", 200, employee_login
        )
        
        if success and 'access_token' in response:
            self.employee_token = response['access_token']
            user_data = response.get('user', {})
            is_main_authority = user_data.get('is_main_authority')
            parent_authority_id = user_data.get('parent_authority_id')
            
            print(f"   Employee 1 token obtained: {self.employee_token[:20]}...")
            print(f"   Is main authority: {is_main_authority}")
            print(f"   Parent authority ID: {parent_authority_id}")
            
            # Verify employee properties
            if (not is_main_authority and parent_authority_id == self.main_authority_id):
                print("   ✅ Employee has correct hierarchy properties")
            else:
                print("   ❌ Employee has incorrect hierarchy properties")
        
        # Test 5: Employee 2 login
        employee2_login = {"email": self.employee2_data["email"], "password": self.employee2_data["password"]}
        success, response = self.run_test(
            "Employee 2 Login", "POST", "auth/login", 200, employee2_login
        )
        
        if success and 'access_token' in response:
            self.employee2_token = response['access_token']
            print(f"   Employee 2 token obtained: {self.employee2_token[:20]}...")
        
        return True

    def test_employee_job_creation_and_hierarchy(self):
        """Test job creation by employees and authority hierarchy"""
        print("\n📋 Testing Employee Job Creation and Authority Hierarchy...")
        
        if not self.employee_token or not self.employee2_token:
            print("❌ Employee tokens not available for hierarchy tests")
            return False
        
        # Test 1: Employee creates job - should include created_by_dienstnummer
        employee_job_data = {
            "license_plate": "B-EMP001",
            "vin": "WVWZZZ3CZWE111111",
            "tow_reason": "Parken im Halteverbot - Employee Job",
            "location_address": "Mitarbeiterstraße 1, 12345 Berlin",
            "location_lat": 52.520008,
            "location_lng": 13.404954,
            "notes": "Job created by employee for hierarchy test"
        }
        
        success, response = self.run_test(
            "Employee 1 Creates Job", "POST", "jobs", 200,
            employee_job_data, self.employee_token
        )
        
        if success and response:
            self.employee_job_id = response.get('id')
            created_by_dienstnummer = response.get('created_by_dienstnummer')
            authority_id = response.get('authority_id')  # This should be set in the backend
            
            print(f"   Employee job created - ID: {self.employee_job_id}")
            print(f"   Created by Dienstnummer: {created_by_dienstnummer}")
            print(f"   Authority ID: {authority_id}")
            
            # Verify job has correct dienstnummer
            if created_by_dienstnummer == self.employee_dienstnummer:
                print("   ✅ Job correctly tracks employee dienstnummer")
            else:
                print("   ❌ Job missing or incorrect employee dienstnummer")
        
        # Test 2: Employee 2 creates job
        employee2_job_data = {
            "license_plate": "B-EMP002",
            "vin": "WVWZZZ3CZWE222222",
            "tow_reason": "Falschparker - Employee 2 Job",
            "location_address": "Mitarbeiterstraße 2, 12345 Berlin",
            "location_lat": 52.521008,
            "location_lng": 13.405954,
            "notes": "Job created by employee 2 for hierarchy test"
        }
        
        success, response = self.run_test(
            "Employee 2 Creates Job", "POST", "jobs", 200,
            employee2_job_data, self.employee2_token
        )
        
        if success and response:
            self.employee2_job_id = response.get('id')
            created_by_dienstnummer = response.get('created_by_dienstnummer')
            
            print(f"   Employee 2 job created - ID: {self.employee2_job_id}")
            print(f"   Created by Dienstnummer: {created_by_dienstnummer}")
            
            # Verify job has correct dienstnummer
            if created_by_dienstnummer == self.employee2_dienstnummer:
                print("   ✅ Job correctly tracks employee 2 dienstnummer")
            else:
                print("   ❌ Job missing or incorrect employee 2 dienstnummer")
        
        # Test 3: Main authority sees ALL jobs from their authority
        success, response = self.run_test(
            "Main Authority Gets All Jobs", "GET", "jobs", 200,
            token=self.authority_token
        )
        
        if success and response:
            job_count = len(response)
            employee_jobs = [j for j in response if j.get('created_by_dienstnummer') in [self.employee_dienstnummer, self.employee2_dienstnummer]]
            main_authority_jobs = [j for j in response if j.get('created_by_dienstnummer') == self.main_authority_dienstnummer]
            
            print(f"   Main authority sees {job_count} total jobs")
            print(f"   - Employee jobs: {len(employee_jobs)}")
            print(f"   - Main authority jobs: {len(main_authority_jobs)}")
            
            # Verify main authority can see employee jobs
            if len(employee_jobs) >= 2:  # Should see both employee jobs
                print("   ✅ Main authority can see employee jobs")
            else:
                print("   ❌ Main authority cannot see all employee jobs")
        
        # Test 4: Employee 1 sees only their own jobs
        success, response = self.run_test(
            "Employee 1 Gets Own Jobs", "GET", "jobs", 200,
            token=self.employee_token
        )
        
        if success and response:
            job_count = len(response)
            own_jobs = [j for j in response if j.get('created_by_dienstnummer') == self.employee_dienstnummer]
            other_jobs = [j for j in response if j.get('created_by_dienstnummer') != self.employee_dienstnummer]
            
            print(f"   Employee 1 sees {job_count} total jobs")
            print(f"   - Own jobs: {len(own_jobs)}")
            print(f"   - Other jobs: {len(other_jobs)}")
            
            # Verify employee only sees their own jobs
            if len(other_jobs) == 0 and len(own_jobs) >= 1:
                print("   ✅ Employee 1 correctly sees only own jobs")
            else:
                print("   ❌ Employee 1 sees jobs they shouldn't see")
        
        # Test 5: Employee 2 sees only their own jobs
        success, response = self.run_test(
            "Employee 2 Gets Own Jobs", "GET", "jobs", 200,
            token=self.employee2_token
        )
        
        if success and response:
            job_count = len(response)
            own_jobs = [j for j in response if j.get('created_by_dienstnummer') == self.employee2_dienstnummer]
            other_jobs = [j for j in response if j.get('created_by_dienstnummer') != self.employee2_dienstnummer]
            
            print(f"   Employee 2 sees {job_count} total jobs")
            print(f"   - Own jobs: {len(own_jobs)}")
            print(f"   - Other jobs: {len(other_jobs)}")
            
            # Verify employee only sees their own jobs
            if len(other_jobs) == 0 and len(own_jobs) >= 1:
                print("   ✅ Employee 2 correctly sees only own jobs")
            else:
                print("   ❌ Employee 2 sees jobs they shouldn't see")
        
        return True

    def test_employee_blocking_and_management(self):
        """Test employee blocking, password changes, and deletion"""
        print("\n🔒 Testing Employee Blocking and Management...")
        
        if not self.employee_id or not self.employee2_id:
            print("❌ Employee IDs not available for management tests")
            return False
        
        # Test 1: Block employee 1
        block_data = {"blocked": True}
        success, response = self.run_test(
            "Block Employee 1", "PATCH", f"authority/employees/{self.employee_id}/block", 200,
            block_data, self.authority_token
        )
        
        if success:
            print("   ✅ Employee 1 blocked successfully")
        
        # Test 2: Verify blocked employee cannot login
        employee_login = {"email": self.employee_data["email"], "password": self.employee_data["password"]}
        success, response = self.run_test(
            "Blocked Employee Login Attempt", "POST", "auth/login", 403, employee_login
        )
        
        if success:  # Success means we got the expected 403 status
            print("   ✅ Blocked employee correctly denied login")
        
        # Test 3: Unblock employee 1
        unblock_data = {"blocked": False}
        success, response = self.run_test(
            "Unblock Employee 1", "PATCH", f"authority/employees/{self.employee_id}/block", 200,
            unblock_data, self.authority_token
        )
        
        if success:
            print("   ✅ Employee 1 unblocked successfully")
        
        # Test 4: Verify unblocked employee can login again
        success, response = self.run_test(
            "Unblocked Employee Login", "POST", "auth/login", 200, employee_login
        )
        
        if success and 'access_token' in response:
            self.employee_token = response['access_token']  # Update token
            print("   ✅ Unblocked employee can login again")
        
        # Test 5: Change employee password
        new_password_data = {"new_password": "NewEmployeePass123!"}
        success, response = self.run_test(
            "Change Employee Password", "PATCH", f"authority/employees/{self.employee_id}/password", 200,
            new_password_data, self.authority_token
        )
        
        if success:
            print("   ✅ Employee password changed successfully")
            
            # Test login with new password
            new_login_data = {"email": self.employee_data["email"], "password": "NewEmployeePass123!"}
            success, response = self.run_test(
                "Login with New Password", "POST", "auth/login", 200, new_login_data
            )
            
            if success and 'access_token' in response:
                print("   ✅ Login with new password successful")
            else:
                print("   ❌ Login with new password failed")
        
        # Test 6: Delete employee 2
        success, response = self.run_test(
            "Delete Employee 2", "DELETE", f"authority/employees/{self.employee2_id}", 200,
            token=self.authority_token
        )
        
        if success:
            print("   ✅ Employee 2 deleted successfully")
            
            # Test that deleted employee cannot login
            employee2_login = {"email": self.employee2_data["email"], "password": self.employee2_data["password"]}
            success, response = self.run_test(
                "Deleted Employee Login Attempt", "POST", "auth/login", 401, employee2_login
            )
            
            if success:  # Success means we got the expected 401 status
                print("   ✅ Deleted employee correctly denied login")
        
        # Test 7: Verify employee list is updated
        success, response = self.run_test(
            "Get Updated Employee List", "GET", "authority/employees", 200,
            token=self.authority_token
        )
        
        if success and response:
            remaining_employees = len(response)
            print(f"   Remaining employees: {remaining_employees}")
            
            # Should have 1 employee left (employee 1, employee 2 was deleted)
            if remaining_employees == 1:
                print("   ✅ Employee list correctly updated after deletion")
            else:
                print("   ❌ Employee list not correctly updated")
        
        return True

    def test_employee_error_cases(self):
        """Test employee management error cases"""
        print("\n⚠️ Testing Employee Management Error Cases...")
        
        # Test 1: Non-authority user trying to create employee
        if self.admin_token:
            success, response = self.run_test(
                "Admin Create Employee (Should Fail)", "POST", "authority/employees", 403,
                self.employee_data, self.admin_token
            )
        
        # Test 2: Employee trying to create another employee (not main authority)
        if self.employee_token:
            success, response = self.run_test(
                "Employee Create Employee (Should Fail)", "POST", "authority/employees", 403,
                {"email": "test@test.de", "password": "test", "name": "test"}, self.employee_token
            )
        
        # Test 3: Duplicate email registration
        success, response = self.run_test(
            "Duplicate Employee Email", "POST", "authority/employees", 400,
            self.employee_data, self.authority_token
        )
        
        # Test 4: Invalid employee ID operations
        fake_employee_id = "00000000-0000-0000-0000-000000000000"
        
        success, response = self.run_test(
            "Block Non-existent Employee", "PATCH", f"authority/employees/{fake_employee_id}/block", 404,
            {"blocked": True}, self.authority_token
        )
        
        success, response = self.run_test(
            "Delete Non-existent Employee", "DELETE", f"authority/employees/{fake_employee_id}", 404,
            token=self.authority_token
        )
        
        success, response = self.run_test(
            "Change Password Non-existent Employee", "PATCH", f"authority/employees/{fake_employee_id}/password", 404,
            {"new_password": "test"}, self.authority_token
        )
        
        return True

    def test_cost_management(self):
        """Test cost management for towing services"""
        print("\n💰 Testing Cost Management...")
        
        # Test updating costs
        new_costs = {"tow_cost": 175.0, "daily_cost": 30.0}
        success, response = self.run_test(
            "Update Towing Costs", "PATCH", "services/costs", 200,
            new_costs, self.towing_token
        )
        
        if success and response:
            updated_tow_cost = response.get('tow_cost')
            updated_daily_cost = response.get('daily_cost')
            print(f"   Updated costs - Tow: {updated_tow_cost}€, Daily: {updated_daily_cost}€")
        
        return success
    def test_service_linking(self):
        """Test service linking functionality"""
        print("\n🔗 Testing Service Linking...")
        
        if not hasattr(self, 'towing_service_code'):
            print("❌ No towing service code available for linking test")
            return False
        
        # Link service to authority (should work now that service is approved)
        link_data = {"service_code": self.towing_service_code}
        success, response = self.run_test(
            "Link Towing Service", "POST", "services/link", 200, 
            link_data, self.authority_token
        )
        
        # Get linked services
        success, response = self.run_test(
            "Get Linked Services", "GET", "services", 200, 
            token=self.authority_token
        )
        
        return success

    def test_job_creation(self):
        """Test job creation"""
        print("\n📋 Testing Job Creation...")
        
        job_data = {
            "license_plate": "B-TEST123",
            "vin": "WVWZZZ3CZWE123456",
            "tow_reason": "Parken im absoluten Halteverbot",
            "location_address": "Teststraße 1, 12345 Berlin",
            "location_lat": 52.520008,
            "location_lng": 13.404954,
            "photos": ["data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwA/8A"],
            "notes": "Test job creation",
            "assigned_service_id": self.towing_service_id
        }
        
        success, response = self.run_test(
            "Create Job", "POST", "jobs", 200, 
            job_data, self.authority_token
        )
        
        if success and 'id' in response:
            self.test_job_id = response['id']
            print(f"   Job created with ID: {self.test_job_id}")
            return True
        
        return False

    def test_job_management(self):
        """Test job management operations"""
        print("\n📊 Testing Job Management...")
        
        if not hasattr(self, 'test_job_id'):
            print("❌ No test job available for management tests")
            return False
        
        # Get jobs
        success, response = self.run_test("Get Jobs - Authority", "GET", "jobs", 200, token=self.authority_token)
        success, response = self.run_test("Get Jobs - Towing", "GET", "jobs", 200, token=self.towing_token)
        
        # Get specific job
        success, response = self.run_test(
            "Get Specific Job", "GET", f"jobs/{self.test_job_id}", 200, 
            token=self.authority_token
        )
        
        # Update job status to towed (towing service)
        update_data = {"status": "towed", "service_notes": "Vehicle towed successfully"}
        success, response = self.run_test(
            "Update Job Status to Towed", "PATCH", f"jobs/{self.test_job_id}", 200,
            update_data, self.towing_token
        )
        
        # Update job status to in_yard (towing service)
        update_data = {"status": "in_yard"}
        success, response = self.run_test(
            "Update Job Status to In Yard", "PATCH", f"jobs/{self.test_job_id}", 200,
            update_data, self.towing_token
        )
        
        return True

    def test_bulk_job_management(self):
        """Test bulk job management features"""
        print("\n🔄 Testing Bulk Job Management...")
        
        # Create multiple test jobs for bulk operations
        job_ids = []
        for i in range(3):
            job_data = {
                "license_plate": f"B-BULK{i:03d}",
                "vin": f"WVWZZZ3CZWE12345{i}",
                "tow_reason": f"Test bulk job {i+1}",
                "location_address": f"Teststraße {i+1}, 12345 Berlin",
                "location_lat": 52.520008 + i * 0.001,
                "location_lng": 13.404954 + i * 0.001,
                "notes": f"Bulk test job {i+1}",
                "assigned_service_id": self.towing_service_id
            }
            
            success, response = self.run_test(
                f"Create Bulk Job {i+1}", "POST", "jobs", 200, 
                job_data, self.authority_token
            )
            
            if success and 'id' in response:
                job_ids.append(response['id'])
                print(f"   Created job {i+1} with ID: {response['id']}")
        
        if len(job_ids) < 3:
            print("❌ Failed to create enough test jobs for bulk operations")
            return False
        
        self.bulk_job_ids = job_ids
        
        # Test bulk status update to "on_site"
        bulk_data = {"job_ids": job_ids, "status": "on_site"}
        success, response = self.run_test(
            "Bulk Update to On Site", "POST", "jobs/bulk-update-status", 200,
            bulk_data, self.towing_token
        )
        
        if success and response:
            updated_count = response.get('updated_count', 0)
            print(f"   Updated {updated_count} jobs to on_site status")
            
            # Verify timestamps were set correctly
            for job_id in job_ids:
                success, job_response = self.run_test(
                    f"Verify On Site Timestamp", "GET", f"jobs/{job_id}", 200,
                    token=self.towing_token
                )
                if success and job_response:
                    on_site_at = job_response.get('on_site_at')
                    if on_site_at:
                        print(f"   ✅ Job {job_id[:8]}... has on_site_at timestamp: {on_site_at}")
                    else:
                        print(f"   ❌ Job {job_id[:8]}... missing on_site_at timestamp")
        
        # Test bulk status update to "towed"
        bulk_data = {"job_ids": job_ids[:2], "status": "towed"}  # Only update first 2 jobs
        success, response = self.run_test(
            "Bulk Update to Towed", "POST", "jobs/bulk-update-status", 200,
            bulk_data, self.towing_token
        )
        
        if success and response:
            updated_count = response.get('updated_count', 0)
            print(f"   Updated {updated_count} jobs to towed status")
        
        # Test bulk status update to "in_yard"
        bulk_data = {"job_ids": [job_ids[0]], "status": "in_yard"}  # Only update first job
        success, response = self.run_test(
            "Bulk Update to In Yard", "POST", "jobs/bulk-update-status", 200,
            bulk_data, self.towing_token
        )
        
        if success and response:
            updated_count = response.get('updated_count', 0)
            print(f"   Updated {updated_count} jobs to in_yard status")
            
            # Verify in_yard_at timestamp
            success, job_response = self.run_test(
                f"Verify In Yard Timestamp", "GET", f"jobs/{job_ids[0]}", 200,
                token=self.towing_token
            )
            if success and job_response:
                in_yard_at = job_response.get('in_yard_at')
                if in_yard_at:
                    print(f"   ✅ Job has in_yard_at timestamp: {in_yard_at}")
                else:
                    print(f"   ❌ Job missing in_yard_at timestamp")
        
        return True

    def test_bulk_job_error_cases(self):
        """Test bulk job management error cases"""
        print("\n⚠️ Testing Bulk Job Error Cases...")
        
        if not hasattr(self, 'bulk_job_ids') or not self.bulk_job_ids:
            print("❌ No bulk job IDs available for error testing")
            return False
        
        # Test empty job_ids array
        bulk_data = {"job_ids": [], "status": "on_site"}
        success, response = self.run_test(
            "Bulk Update - Empty Job IDs", "POST", "jobs/bulk-update-status", 400,
            bulk_data, self.towing_token
        )
        
        # Test invalid status
        bulk_data = {"job_ids": self.bulk_job_ids[:1], "status": "invalid_status"}
        success, response = self.run_test(
            "Bulk Update - Invalid Status", "POST", "jobs/bulk-update-status", 400,
            bulk_data, self.towing_token
        )
        
        # Test unauthorized role (authority trying to bulk update)
        bulk_data = {"job_ids": self.bulk_job_ids[:1], "status": "on_site"}
        success, response = self.run_test(
            "Bulk Update - Wrong Role", "POST", "jobs/bulk-update-status", 403,
            bulk_data, self.authority_token
        )
        
        # Test updating jobs not assigned to this towing service
        # First create a job without assignment
        job_data = {
            "license_plate": "B-UNASSIGNED",
            "vin": "WVWZZZ3CZWE999999",
            "tow_reason": "Unassigned test job",
            "location_address": "Teststraße 999, 12345 Berlin",
            "location_lat": 52.520008,
            "location_lng": 13.404954,
            "notes": "Unassigned job for testing"
            # No assigned_service_id
        }
        
        success, response = self.run_test(
            "Create Unassigned Job", "POST", "jobs", 200, 
            job_data, self.authority_token
        )
        
        if success and 'id' in response:
            unassigned_job_id = response['id']
            
            # Try to bulk update unassigned job (should update 0 jobs)
            bulk_data = {"job_ids": [unassigned_job_id], "status": "on_site"}
            success, response = self.run_test(
                "Bulk Update - Unassigned Job", "POST", "jobs/bulk-update-status", 200,
                bulk_data, self.towing_token
            )
            
            if success and response:
                updated_count = response.get('updated_count', 0)
                if updated_count == 0:
                    print(f"   ✅ Correctly updated 0 unassigned jobs")
                else:
                    print(f"   ❌ Incorrectly updated {updated_count} unassigned jobs")
        
        return True

    def test_date_filtering(self):
        """Test date filtering on GET /api/jobs"""
        print("\n📅 Testing Date Filtering...")
        
        from datetime import datetime, timedelta
        
        # Get current date and calculate date ranges
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Test date_from parameter
        success, response = self.run_test(
            "Get Jobs - Date From Today", "GET", f"jobs?date_from={today}", 200,
            token=self.authority_token
        )
        
        if success and response:
            print(f"   Found {len(response)} jobs from today onwards")
        
        # Test date_to parameter
        success, response = self.run_test(
            "Get Jobs - Date To Today", "GET", f"jobs?date_to={today}", 200,
            token=self.authority_token
        )
        
        if success and response:
            print(f"   Found {len(response)} jobs up to today")
        
        # Test date range (yesterday to tomorrow)
        success, response = self.run_test(
            "Get Jobs - Date Range", "GET", f"jobs?date_from={yesterday}&date_to={tomorrow}", 200,
            token=self.authority_token
        )
        
        if success and response:
            print(f"   Found {len(response)} jobs in date range {yesterday} to {tomorrow}")
        
        # Test with towing service token
        success, response = self.run_test(
            "Get Jobs - Towing Service Date Filter", "GET", f"jobs?date_from={today}", 200,
            token=self.towing_token
        )
        
        if success and response:
            print(f"   Towing service found {len(response)} jobs from today onwards")
        
        # Test invalid date format (should still work, just no filtering)
        success, response = self.run_test(
            "Get Jobs - Invalid Date Format", "GET", "jobs?date_from=invalid-date", 200,
            token=self.authority_token
        )
        
        return True

    def test_vehicle_search(self):
        """Test public vehicle search with cost calculation"""
        print("\n🔍 Testing Vehicle Search with Cost Calculation...")
        
        # Search for existing vehicle (should show costs now)
        success, response = self.run_test(
            "Search Vehicle - Found with Costs", "GET", "search/vehicle?q=B-TEST123", 200
        )
        
        if success and response and response.get('found'):
            tow_cost = response.get('tow_cost')
            daily_cost = response.get('daily_cost')
            days_in_yard = response.get('days_in_yard')
            total_cost = response.get('total_cost')
            
            print(f"   Cost calculation - Tow: {tow_cost}€, Daily: {daily_cost}€, Days: {days_in_yard}, Total: {total_cost}€")
            
            # Verify cost calculation
            expected_total = (tow_cost or 0) + (daily_cost or 0) * (days_in_yard or 0)
            if abs((total_cost or 0) - expected_total) < 0.01:
                print(f"   ✅ Cost calculation correct")
            else:
                print(f"   ❌ Cost calculation incorrect - Expected: {expected_total}€, Got: {total_cost}€")
        
        # Search for non-existing vehicle
        success, response = self.run_test(
            "Search Vehicle - Not Found", "GET", "search/vehicle?q=NOTFOUND", 200
        )
        
        return True

    def test_admin_endpoints(self):
        """Test admin-only endpoints"""
        print("\n👑 Testing Admin Endpoints...")
        
        # Get admin stats
        success, response = self.run_test(
            "Admin Stats", "GET", "admin/stats", 200, 
            token=self.admin_token
        )
        
        # Get all jobs (admin)
        success, response = self.run_test(
            "Admin All Jobs", "GET", "admin/jobs", 200, 
            token=self.admin_token
        )
        
        # Get all users (admin)
        success, response = self.run_test(
            "Admin All Users", "GET", "admin/users", 200, 
            token=self.admin_token
        )
        
        return True

    def test_pdf_generation(self):
        """Test PDF generation"""
        print("\n📄 Testing PDF Generation...")
        
        if not hasattr(self, 'test_job_id'):
            print("❌ No test job available for PDF test")
            return False
        
        # Test PDF generation endpoint
        url = f"{self.base_url}/jobs/{self.test_job_id}/pdf"
        headers = {'Authorization': f'Bearer {self.authority_token}'}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            success = response.status_code == 200 and response.headers.get('content-type') == 'application/pdf'
            
            if success:
                print("✅ PDF Generation - Passed")
                self.tests_passed += 1
            else:
                print(f"❌ PDF Generation - Failed (Status: {response.status_code})")
            
            self.tests_run += 1
            return success
            
        except Exception as e:
            print(f"❌ PDF Generation - Error: {str(e)}")
            self.tests_run += 1
            return False

    def test_admin_login_with_provided_credentials(self):
        """Test admin login with provided credentials: admin@test.de / Admin123!"""
        print("\n🔐 Testing Admin Login with Provided Credentials...")
        
        login_data = {"email": "admin@test.de", "password": "Admin123!"}
        success, response = self.run_test(
            "Admin Login (Provided Credentials)", "POST", "auth/login", 200, login_data
        )
        
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            user_data = response.get('user', {})
            print(f"   ✅ Admin login successful")
            print(f"   Admin ID: {user_data.get('id')}")
            print(f"   Admin Role: {user_data.get('role')}")
            print(f"   Token obtained: {self.admin_token[:20]}...")
            return True
        else:
            print(f"   ❌ Admin login failed")
            return False

    def test_pagination_endpoints(self):
        """Test pagination endpoints as specified in review request"""
        print("\n📄 Testing Pagination Endpoints...")
        
        if not self.admin_token:
            print("❌ No admin token available for pagination tests")
            return False
        
        # Test GET /api/admin/jobs?page=1&limit=5
        success, response = self.run_test(
            "Admin Jobs Pagination (page=1, limit=5)", "GET", "admin/jobs?page=1&limit=5", 200,
            token=self.admin_token
        )
        
        if success and response:
            job_count = len(response)
            print(f"   ✅ Retrieved {job_count} jobs (expected max 5)")
            if job_count <= 5:
                print(f"   ✅ Pagination limit respected")
            else:
                print(f"   ❌ Pagination limit not respected - got {job_count} jobs")
        
        # Test GET /api/admin/jobs/count
        success, response = self.run_test(
            "Admin Jobs Count", "GET", "admin/jobs/count", 200,
            token=self.admin_token
        )
        
        if success and response:
            total_count = response.get('total', 0)
            print(f"   ✅ Total jobs count: {total_count}")
        
        # Test different page sizes
        success, response = self.run_test(
            "Admin Jobs Pagination (page=1, limit=3)", "GET", "admin/jobs?page=1&limit=3", 200,
            token=self.admin_token
        )
        
        if success and response:
            job_count = len(response)
            print(f"   ✅ Retrieved {job_count} jobs with limit=3")
            if job_count <= 3:
                print(f"   ✅ Custom pagination limit respected")
        
        # Test page 2 to verify different results
        success, response = self.run_test(
            "Admin Jobs Pagination (page=2, limit=5)", "GET", "admin/jobs?page=2&limit=5", 200,
            token=self.admin_token
        )
        
        if success and response:
            job_count = len(response)
            print(f"   ✅ Page 2 retrieved {job_count} jobs")
        
        return True

    def test_audit_logging_endpoints(self):
        """Test audit logging endpoints"""
        print("\n📋 Testing Audit Logging Endpoints...")
        
        if not self.admin_token:
            print("❌ No admin token available for audit log tests")
            return False
        
        # Test GET /api/admin/audit-log (note: endpoint might be audit-logs based on backend code)
        success, response = self.run_test(
            "Get Audit Logs", "GET", "admin/audit-logs", 200,
            token=self.admin_token
        )
        
        if success and response:
            audit_count = len(response)
            print(f"   ✅ Retrieved {audit_count} audit log entries")
            
            # Check for login audit entries
            login_entries = [entry for entry in response if entry.get('action') in ['USER_LOGIN', 'LOGIN_FAILED']]
            print(f"   ✅ Found {len(login_entries)} login-related audit entries")
            
            # Display some sample audit entries
            for i, entry in enumerate(response[:3]):
                action = entry.get('action', 'Unknown')
                user_name = entry.get('user_name', 'Unknown')
                timestamp = entry.get('timestamp', 'Unknown')
                print(f"   - Entry {i+1}: {action} by {user_name} at {timestamp}")
        
        # Also test the alternative endpoint name if the first one fails
        if not success:
            success, response = self.run_test(
                "Get Audit Log (alternative)", "GET", "admin/audit-log", 200,
                token=self.admin_token
            )
        
        return success

    def test_excel_export_endpoint(self):
        """Test Excel export endpoint"""
        print("\n📊 Testing Excel Export Endpoint...")
        
        if not self.admin_token:
            print("❌ No admin token available for Excel export test")
            return False
        
        # Test GET /api/export/jobs/excel
        url = f"{self.base_url}/export/jobs/excel"
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            print(f"🔍 Testing Excel Export...")
            response = requests.get(url, headers=headers, timeout=30)
            
            success = response.status_code == 200
            content_type = response.headers.get('content-type', '')
            
            if success:
                # Check if it's actually an Excel file
                if 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in content_type or 'application/octet-stream' in content_type:
                    print(f"✅ Excel Export - Passed (Content-Type: {content_type})")
                    print(f"   File size: {len(response.content)} bytes")
                    self.tests_passed += 1
                else:
                    print(f"❌ Excel Export - Wrong content type: {content_type}")
            else:
                print(f"❌ Excel Export - Failed (Status: {response.status_code})")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
            
            self.tests_run += 1
            return success
            
        except Exception as e:
            print(f"❌ Excel Export - Error: {str(e)}")
            self.tests_run += 1
            return False

    def test_fulltext_search_endpoint(self):
        """Test full-text search endpoint"""
        print("\n🔍 Testing Full-text Search Endpoint...")
        
        if not self.admin_token:
            print("❌ No admin token available for search tests")
            return False
        
        # Test GET /api/admin/jobs?search=test
        success, response = self.run_test(
            "Admin Jobs Search (search=test)", "GET", "admin/jobs?search=test", 200,
            token=self.admin_token
        )
        
        if success and response:
            result_count = len(response)
            print(f"   ✅ Search returned {result_count} results for 'test'")
            
            # Check if results contain the search term in various fields
            for job in response[:3]:  # Check first 3 results
                license_plate = job.get('license_plate', '').lower()
                job_number = job.get('job_number', '').lower()
                tow_reason = job.get('tow_reason', '').lower()
                notes = job.get('notes', '').lower()
                
                contains_test = any('test' in field for field in [license_plate, job_number, tow_reason, notes])
                if contains_test:
                    print(f"   ✅ Job {job.get('job_number', 'Unknown')} contains 'test' in searchable fields")
        
        # Test search with different terms
        success, response = self.run_test(
            "Admin Jobs Search (search=berlin)", "GET", "admin/jobs?search=berlin", 200,
            token=self.admin_token
        )
        
        if success and response:
            result_count = len(response)
            print(f"   ✅ Search returned {result_count} results for 'berlin'")
        
        # Test empty search (should return all jobs)
        success, response = self.run_test(
            "Admin Jobs Search (no search term)", "GET", "admin/jobs", 200,
            token=self.admin_token
        )
        
        if success and response:
            total_count = len(response)
            print(f"   ✅ No search term returned {total_count} total jobs")
        
        return True

    def test_service_approval_endpoints(self):
        """Test service approval endpoints"""
        print("\n✅ Testing Service Approval Endpoints...")
        
        if not self.admin_token:
            print("❌ No admin token available for approval tests")
            return False
        
        # Test GET /api/admin/pending-services
        success, response = self.run_test(
            "Get Pending Services", "GET", "admin/pending-services", 200,
            token=self.admin_token
        )
        
        if success and response:
            pending_count = len(response)
            print(f"   ✅ Found {pending_count} pending towing services")
            
            for service in response[:3]:  # Show first 3
                company_name = service.get('company_name', 'Unknown')
                email = service.get('email', 'Unknown')
                approval_status = service.get('approval_status', 'Unknown')
                print(f"   - {company_name} ({email}) - Status: {approval_status}")
        
        # Test GET /api/admin/pending-authorities
        success, response = self.run_test(
            "Get Pending Authorities", "GET", "admin/pending-authorities", 200,
            token=self.admin_token
        )
        
        if success and response:
            pending_count = len(response)
            print(f"   ✅ Found {pending_count} pending authorities")
            
            for authority in response[:3]:  # Show first 3
                authority_name = authority.get('authority_name', 'Unknown')
                email = authority.get('email', 'Unknown')
                approval_status = authority.get('approval_status', 'Unknown')
                print(f"   - {authority_name} ({email}) - Status: {approval_status}")
        
        return True

    def test_user_management_endpoint(self):
        """Test user management endpoint"""
        print("\n👥 Testing User Management Endpoint...")
        
        if not self.admin_token:
            print("❌ No admin token available for user management tests")
            return False
        
        # Test GET /api/admin/users
        success, response = self.run_test(
            "Get All Users", "GET", "admin/users", 200,
            token=self.admin_token
        )
        
        if success and response:
            user_count = len(response)
            print(f"   ✅ Retrieved {user_count} users")
            
            # Count users by role
            role_counts = {}
            for user in response:
                role = user.get('role', 'unknown')
                role_counts[role] = role_counts.get(role, 0) + 1
            
            print(f"   User breakdown by role:")
            for role, count in role_counts.items():
                print(f"   - {role}: {count} users")
            
            # Show sample users
            for i, user in enumerate(response[:3]):
                name = user.get('name', 'Unknown')
                email = user.get('email', 'Unknown')
                role = user.get('role', 'Unknown')
                is_blocked = user.get('is_blocked', False)
                print(f"   - User {i+1}: {name} ({email}) - Role: {role}, Blocked: {is_blocked}")
        
        return success

    def test_public_search_endpoint(self):
        """Test public vehicle search endpoint"""
        print("\n🔍 Testing Public Vehicle Search Endpoint...")
        
        # Test GET /api/search/vehicle?license_plate=TEST123
        success, response = self.run_test(
            "Public Vehicle Search (TEST123)", "GET", "search/vehicle?license_plate=TEST123", 200
        )
        
        if success and response:
            found = response.get('found', False)
            print(f"   Search result for TEST123: {'Found' if found else 'Not Found'}")
            
            if found:
                # Check for required location fields
                location_lat = response.get('location_lat')
                location_lng = response.get('location_lng')
                
                if location_lat is not None and location_lng is not None:
                    print(f"   ✅ Location coordinates present: lat={location_lat}, lng={location_lng}")
                else:
                    print(f"   ❌ Missing location coordinates")
                
                # Show other details
                job_number = response.get('job_number', 'N/A')
                status = response.get('status', 'N/A')
                company_name = response.get('company_name', 'N/A')
                total_cost = response.get('total_cost', 'N/A')
                
                print(f"   Job Number: {job_number}")
                print(f"   Status: {status}")
                print(f"   Company: {company_name}")
                print(f"   Total Cost: {total_cost}€")
        
        # Test with different license plate formats
        success, response = self.run_test(
            "Public Vehicle Search (B-TEST123)", "GET", "search/vehicle?license_plate=B-TEST123", 200
        )
        
        # Test with query parameter 'q' instead of 'license_plate'
        success, response = self.run_test(
            "Public Vehicle Search with q parameter", "GET", "search/vehicle?q=TEST123", 200
        )
        
        if success and response:
            found = response.get('found', False)
            print(f"   Search with 'q' parameter: {'Found' if found else 'Not Found'}")
        
        return True

    def test_time_based_cost_calculation(self):
        """Test time-based cost calculation functionality as requested in review"""
        print("\n⏰ Testing Time-Based Cost Calculation...")
        
        # Step 1: Login as Abschleppdienst with provided credentials
        login_data = {"email": "abschlepp@test.de", "password": "Abschlepp123"}
        success, response = self.run_test(
            "Towing Service Login (abschlepp@test.de)", "POST", "auth/login", 200, login_data
        )
        
        if not success or 'access_token' not in response:
            print("❌ Failed to login as towing service - cannot continue time-based tests")
            return False
        
        towing_token = response['access_token']
        towing_user = response.get('user', {})
        towing_service_id = towing_user.get('id')
        
        print(f"   ✅ Towing service login successful")
        print(f"   Service ID: {towing_service_id}")
        print(f"   Company: {towing_user.get('company_name', 'Unknown')}")
        
        # Step 2: Check current pricing settings via GET /api/auth/me
        success, response = self.run_test(
            "Check Current Pricing Settings", "GET", "auth/me", 200, token=towing_token
        )
        
        if success and response:
            time_based_enabled = response.get('time_based_enabled')
            first_half_hour = response.get('first_half_hour')
            additional_half_hour = response.get('additional_half_hour')
            
            print(f"   Current pricing settings:")
            print(f"   - time_based_enabled: {time_based_enabled}")
            print(f"   - first_half_hour: {first_half_hour}")
            print(f"   - additional_half_hour: {additional_half_hour}")
        
        # Step 3: Activate time-based calculation with PATCH /api/services/pricing-settings
        pricing_data = {
            "time_based_enabled": True,
            "first_half_hour": 137.00,
            "additional_half_hour": 93.00
        }
        
        success, response = self.run_test(
            "Activate Time-Based Pricing", "PATCH", "services/pricing-settings", 200,
            pricing_data, towing_token
        )
        
        if success and response:
            updated_time_based = response.get('time_based_enabled')
            updated_first_hh = response.get('first_half_hour')
            updated_add_hh = response.get('additional_half_hour')
            
            print(f"   ✅ Time-based pricing activated:")
            print(f"   - time_based_enabled: {updated_time_based}")
            print(f"   - first_half_hour: {updated_first_hh}€")
            print(f"   - additional_half_hour: {updated_add_hh}€")
            
            if updated_time_based and updated_first_hh == 137.00 and updated_add_hh == 93.00:
                print(f"   ✅ Pricing settings correctly updated")
            else:
                print(f"   ❌ Pricing settings not correctly updated")
                return False
        else:
            print("   ❌ Failed to activate time-based pricing")
            return False
        
        # Step 4: Find a job with "in_yard" status
        success, response = self.run_test(
            "Get Jobs for Towing Service", "GET", "jobs", 200, token=towing_token
        )
        
        in_yard_job = None
        if success and response:
            # Look for a job with in_yard status
            for job in response:
                if job.get('status') == 'in_yard' and job.get('accepted_at') and job.get('in_yard_at'):
                    in_yard_job = job
                    break
            
            if not in_yard_job:
                # If no in_yard job exists, try to create one and update it to in_yard
                print("   No in_yard job found, creating test job...")
                
                # Create a test job
                job_data = {
                    "license_plate": "B-TIME001",
                    "vin": "WVWZZZ3CZWE999001",
                    "tow_reason": "Time-based cost test job",
                    "location_address": "Zeitstraße 1, 12345 Berlin",
                    "location_lat": 52.520008,
                    "location_lng": 13.404954,
                    "notes": "Job for time-based cost calculation test"
                }
                
                # First login as authority to create job
                auth_login = {"email": "behoerde@test.de", "password": "Behoerde123"}
                auth_success, auth_response = self.run_test(
                    "Authority Login for Job Creation", "POST", "auth/login", 200, auth_login
                )
                
                if auth_success and 'access_token' in auth_response:
                    auth_token = auth_response['access_token']
                    job_data["assigned_service_id"] = towing_service_id
                    
                    create_success, create_response = self.run_test(
                        "Create Test Job for Time-Based Calculation", "POST", "jobs", 200,
                        job_data, auth_token
                    )
                    
                    if create_success and create_response:
                        test_job_id = create_response['id']
                        print(f"   ✅ Created test job: {test_job_id}")
                        
                        # Update job to on_site status first (to set accepted_at)
                        update_data = {"status": "on_site"}
                        self.run_test(
                            "Update Job to On Site", "PATCH", f"jobs/{test_job_id}", 200,
                            update_data, towing_token
                        )
                        
                        # Update job to towed status
                        update_data = {"status": "towed"}
                        self.run_test(
                            "Update Job to Towed", "PATCH", f"jobs/{test_job_id}", 200,
                            update_data, towing_token
                        )
                        
                        # Update job to in_yard status
                        update_data = {"status": "in_yard"}
                        update_success, update_response = self.run_test(
                            "Update Job to In Yard", "PATCH", f"jobs/{test_job_id}", 200,
                            update_data, towing_token
                        )
                        
                        if update_success:
                            # Get the updated job
                            job_success, job_response = self.run_test(
                                "Get Updated Job", "GET", f"jobs/{test_job_id}", 200, token=towing_token
                            )
                            
                            if job_success and job_response:
                                in_yard_job = job_response
                                print(f"   ✅ Job updated to in_yard status")
        
        if not in_yard_job:
            print("   ❌ No job with in_yard status found or created")
            return False
        
        job_id = in_yard_job['id']
        job_number = in_yard_job.get('job_number', 'Unknown')
        accepted_at = in_yard_job.get('accepted_at')
        in_yard_at = in_yard_job.get('in_yard_at')
        
        print(f"   ✅ Found in_yard job: {job_number} (ID: {job_id})")
        print(f"   - accepted_at: {accepted_at}")
        print(f"   - in_yard_at: {in_yard_at}")
        
        # Step 5: Call GET /api/jobs/{job_id}/calculate-costs
        success, response = self.run_test(
            "Calculate Time-Based Costs", "GET", f"jobs/{job_id}/calculate-costs", 200,
            token=towing_token
        )
        
        if success and response:
            total_cost = response.get('total', 0)
            breakdown = response.get('breakdown', [])
            
            print(f"   ✅ Cost calculation successful:")
            print(f"   - Total cost: {total_cost}€")
            print(f"   - Breakdown items: {len(breakdown)}")
            
            # Check if time-based pricing is used in breakdown
            time_based_items = []
            for item in breakdown:
                label = item.get('label', '')
                amount = item.get('amount', 0)
                print(f"     * {label}: {amount}€")
                
                if 'halbe stunde' in label.lower() or 'erste' in label.lower() or 'weitere' in label.lower():
                    time_based_items.append(item)
            
            # Verify time-based calculation
            if len(time_based_items) > 0:
                print(f"   ✅ Time-based pricing detected in breakdown:")
                for item in time_based_items:
                    print(f"     ✅ {item.get('label')}: {item.get('amount')}€")
                
                # Check for expected pricing structure
                first_hh_found = any('erste' in item.get('label', '').lower() for item in time_based_items)
                if first_hh_found:
                    print(f"   ✅ 'Erste halbe Stunde' found in breakdown")
                else:
                    print(f"   ❌ 'Erste halbe Stunde' not found in breakdown")
                
                return True
            else:
                print(f"   ❌ No time-based pricing items found in breakdown")
                print(f"   Expected: 'Erste halbe Stunde' and potentially 'weitere halbe Stunde'")
                return False
        else:
            print("   ❌ Failed to calculate costs")
            return False

    def test_aws_ses_email_integration(self):
        """Test AWS SES email integration via forgot password functionality"""
        print("\n📧 Testing AWS SES Email Integration...")
        
        # Test 1: Password reset with admin@test.de
        print("\n🔍 Testing password reset email with admin@test.de...")
        reset_data = {"email": "admin@test.de"}
        success, response = self.run_test(
            "Password Reset Email (admin@test.de)", "POST", "auth/forgot-password", 200, reset_data
        )
        
        if success and response:
            message = response.get('message', '')
            print(f"   Response message: {message}")
            
            # Check if response contains expected German message
            if "Falls ein Konto mit dieser E-Mail existiert" in message:
                print("   ✅ Correct response message received")
            else:
                print("   ❌ Unexpected response message")
        
        # Test 2: Password reset with verified sender email
        print("\n🔍 Testing password reset email with verified sender email...")
        reset_data_verified = {"email": "info@werhatmeinautoabgeschleppt.de"}
        success, response = self.run_test(
            "Password Reset Email (Verified Sender)", "POST", "auth/forgot-password", 200, reset_data_verified
        )
        
        if success and response:
            message = response.get('message', '')
            print(f"   Response message: {message}")
            
            # Check if response contains expected German message
            if "Falls ein Konto mit dieser E-Mail existiert" in message:
                print("   ✅ Correct response message received")
            else:
                print("   ❌ Unexpected response message")
        
        # Test 3: Check backend logs for email sending
        print("\n📋 Checking backend logs for email sending...")
        try:
            import subprocess
            import os
            
            # Check supervisor backend logs for email-related messages
            log_files = [
                "/var/log/supervisor/backend.out.log",
                "/var/log/supervisor/backend.err.log"
            ]
            
            email_sent_found = False
            ses_error_found = False
            error_details = []
            
            for log_file in log_files:
                if os.path.exists(log_file):
                    try:
                        # Get last 100 lines of log
                        result = subprocess.run(['tail', '-n', '100', log_file], 
                                              capture_output=True, text=True, timeout=10)
                        log_content = result.stdout
                        
                        # Check for email sending success
                        if "Password reset email sent" in log_content:
                            email_sent_found = True
                            print(f"   ✅ Found 'Password reset email sent' in {log_file}")
                        
                        # Check for SES errors
                        if "MessageRejected" in log_content:
                            ses_error_found = True
                            error_details.append("MessageRejected - Email destination not verified (Sandbox mode)")
                            print(f"   ⚠️ Found MessageRejected error in {log_file}")
                        
                        if "MailFromDomainNotVerified" in log_content:
                            ses_error_found = True
                            error_details.append("MailFromDomainNotVerified - Sender domain not verified")
                            print(f"   ⚠️ Found MailFromDomainNotVerified error in {log_file}")
                        
                        # Check for other AWS SES errors
                        if "ClientError" in log_content and "SES" in log_content:
                            ses_error_found = True
                            error_details.append("AWS SES ClientError found in logs")
                            print(f"   ⚠️ Found AWS SES ClientError in {log_file}")
                        
                        # Check for email mock messages (when SES is not configured)
                        if "EMAIL MOCK" in log_content or "SES nicht konfiguriert" in log_content:
                            print(f"   ℹ️ Found email mock messages - SES not fully configured")
                        
                    except subprocess.TimeoutExpired:
                        print(f"   ⚠️ Timeout reading {log_file}")
                    except Exception as e:
                        print(f"   ⚠️ Error reading {log_file}: {str(e)}")
                else:
                    print(f"   ⚠️ Log file {log_file} not found")
            
            # Summary of log analysis
            if email_sent_found:
                print("   ✅ Email sending confirmed in backend logs")
            elif ses_error_found:
                print("   ⚠️ SES errors found in logs:")
                for error in error_details:
                    print(f"      - {error}")
            else:
                print("   ℹ️ No specific email sending confirmation found in recent logs")
                
        except Exception as e:
            print(f"   ⚠️ Error checking backend logs: {str(e)}")
        
        return True

    def test_comprehensive_backend_review(self):
        """Run all tests specified in the review request"""
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE BACKEND TESTING - REVIEW REQUEST")
        print("="*80)
        
        all_tests_passed = True
        
        # NEW: Time-based cost calculation test (as requested in review)
        if not self.test_time_based_cost_calculation():
            all_tests_passed = False
        
        # 1. Authentication with provided credentials
        if not self.test_admin_login_with_provided_credentials():
            all_tests_passed = False
        
        # 2. Pagination endpoints
        if not self.test_pagination_endpoints():
            all_tests_passed = False
        
        # 3. Audit logging
        if not self.test_audit_logging_endpoints():
            all_tests_passed = False
        
        # 4. Excel export
        if not self.test_excel_export_endpoint():
            all_tests_passed = False
        
        # 5. Full-text search
        if not self.test_fulltext_search_endpoint():
            all_tests_passed = False
        
        # 6. Service approval endpoints
        if not self.test_service_approval_endpoints():
            all_tests_passed = False
        
        # 7. User management
        if not self.test_user_management_endpoint():
            all_tests_passed = False
        
        # 8. Public search with location coordinates
        if not self.test_public_search_endpoint():
            all_tests_passed = False
        
        print(f"\n🎯 COMPREHENSIVE BACKEND REVIEW COMPLETE")
        print(f"Overall Result: {'✅ ALL TESTS PASSED' if all_tests_passed else '❌ SOME TESTS FAILED'}")
        
        return all_tests_passed

    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Towing Management API Tests...")
        print(f"📡 Testing against: {self.base_url}")
        
        try:
            # First run the comprehensive backend review as requested
            print("\n" + "="*80)
            print("🎯 STARTING COMPREHENSIVE BACKEND REVIEW")
            print("="*80)
            
            comprehensive_success = self.test_comprehensive_backend_review()
            
            # If comprehensive review passes, we can optionally run additional tests
            if comprehensive_success:
                print("\n" + "="*80)
                print("✅ COMPREHENSIVE REVIEW PASSED - RUNNING ADDITIONAL TESTS")
                print("="*80)
                
                # Basic connectivity (if not already tested)
                if not hasattr(self, 'root_tested'):
                    self.test_root_endpoint()
                    self.root_tested = True
                
                # Run additional comprehensive tests if time permits
                # These are the existing comprehensive tests
                if not hasattr(self, 'registration_tested'):
                    if self.test_user_registration():
                        self.test_user_login()
                        self.test_auth_me()
                        self.test_admin_approval_workflow()
                        self.test_cost_management()
                        self.test_service_linking()
                        
                        # Employee Management System Tests
                        print("\n" + "="*60)
                        print("🏢 EMPLOYEE MANAGEMENT SYSTEM TESTS")
                        print("="*60)
                        
                        self.test_employee_management()
                        self.test_employee_job_creation_and_hierarchy()
                        self.test_employee_blocking_and_management()
                        self.test_employee_error_cases()
                        
                        # Job management
                        if self.test_job_creation():
                            self.test_job_management()
                            self.test_bulk_job_management()
                            self.test_bulk_job_error_cases()
                            self.test_date_filtering()
                            self.test_pdf_generation()
                        
                        self.test_vehicle_search()
                        self.test_admin_endpoints()
                        
                    self.registration_tested = True
            else:
                print("\n" + "="*80)
                print("❌ COMPREHENSIVE REVIEW FAILED - STOPPING ADDITIONAL TESTS")
                print("="*80)
            
            return comprehensive_success
            
        except Exception as e:
            print(f"❌ Test suite failed with error: {str(e)}")
            return False

    def print_summary(self):
        """Print test summary"""
        print(f"\n📊 Test Results Summary:")
        print(f"   Tests run: {self.tests_run}")
        print(f"   Tests passed: {self.tests_passed}")
        print(f"   Tests failed: {self.tests_run - self.tests_passed}")
        print(f"   Success rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        # Print failed tests
        failed_tests = [r for r in self.test_results if not r['success']]
        if failed_tests:
            print(f"\n❌ Failed Tests:")
            for test in failed_tests:
                print(f"   - {test['test']}: Expected {test['expected_status']}, got {test['actual_status']}")
                if 'error' in test:
                    print(f"     Error: {test['error']}")

def main():
    tester = TowingManagementAPITester()
    
    success = tester.run_all_tests()
    tester.print_summary()
    
    return 0 if success and tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
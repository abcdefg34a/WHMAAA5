#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class TowingManagementAPITester:
    def __init__(self, base_url="https://tow-track-system.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.authority_token = None
        self.towing_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # Test data
        self.test_admin = {
            "email": f"admin_{datetime.now().strftime('%H%M%S')}@test.de",
            "password": "TestPass123!",
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

    def test_error_handling(self):
        """Test error handling"""
        print("\n⚠️ Testing Error Handling...")
        
        # Test unauthorized access
        success, response = self.run_test(
            "Unauthorized Access", "GET", "jobs", 403
        )
        
        # Test invalid credentials
        invalid_login = {"email": "invalid@test.de", "password": "wrongpass"}
        success, response = self.run_test(
            "Invalid Login", "POST", "auth/login", 401, invalid_login
        )
        
        # Test duplicate email registration
        success, response = self.run_test(
            "Duplicate Email", "POST", "auth/register", 400, self.test_admin
        )
        
        return True

    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Towing Management API Tests...")
        print(f"📡 Testing against: {self.base_url}")
        
        try:
            # Basic connectivity
            if not self.test_root_endpoint():
                print("❌ Root endpoint failed - stopping tests")
                return False
            
            # Authentication tests
            if not self.test_user_registration():
                print("❌ User registration failed - stopping tests")
                return False
            
            # Test login with pending approval
            self.test_user_login()
            self.test_auth_me()
            
            # Test admin approval workflow
            self.test_admin_approval_workflow()
            
            # Test cost management
            self.test_cost_management()
            
            # Service management (after approval)
            self.test_service_linking()
            
            # NEW: Employee Management System Tests
            print("\n" + "="*60)
            print("🏢 EMPLOYEE MANAGEMENT SYSTEM TESTS")
            print("="*60)
            
            self.test_employee_management()
            self.test_employee_job_creation_and_hierarchy()
            self.test_employee_blocking_and_management()
            self.test_employee_error_cases()
            
            print("\n" + "="*60)
            print("📋 CONTINUING WITH REGULAR JOB TESTS")
            print("="*60)
            
            # Job management
            if self.test_job_creation():
                self.test_job_management()
                
                # Test bulk job management features
                self.test_bulk_job_management()
                self.test_bulk_job_error_cases()
                
                # Test date filtering
                self.test_date_filtering()
                
                self.test_pdf_generation()
            
            # Public endpoints with cost calculation
            self.test_vehicle_search()
            
            # Admin endpoints
            self.test_admin_endpoints()
            
            # Error handling
            self.test_error_handling()
            
            return True
            
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
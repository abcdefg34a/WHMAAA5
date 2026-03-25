#!/usr/bin/env python3
"""
Role-based Access Test for Authority Release
Tests that field employees cannot release vehicles while yard employees can
"""

import requests
import json
import time

# Configuration
BASE_URL = "https://dual-yard-system.preview.emergentagent.com/api"
AUTHORITY_EMAIL = "behoerde@test.de"
AUTHORITY_PASSWORD = "Behoerde123!"

class RoleBasedAccessTester:
    def __init__(self):
        self.session = requests.Session()
        self.authority_token = None
        self.field_employee_token = None
        self.yard_employee_token = None
        self.test_results = []
        self.created_employees = []
        self.test_job_id = None
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        
    def authenticate_authority(self) -> bool:
        """Authenticate as main authority"""
        try:
            response = self.session.post(
                f"{BASE_URL}/auth/login",
                json={
                    "email": AUTHORITY_EMAIL,
                    "password": AUTHORITY_PASSWORD
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.authority_token = data.get("access_token")
                self.log_test("Authority Authentication", True, f"Successfully authenticated as {AUTHORITY_EMAIL}")
                return True
            else:
                self.log_test("Authority Authentication", False, f"Failed with status {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Authority Authentication", False, f"Exception: {str(e)}")
            return False
    
    def create_test_employees(self):
        """Create field and yard employees for testing"""
        headers = {"Authorization": f"Bearer {self.authority_token}"}
        
        # Create field employee
        try:
            field_data = {
                "email": f"field.test.{int(time.time())}@test.de",
                "password": "FieldTest123!",
                "name": "Field Test Employee",
                "sub_role": "field"
            }
            response = requests.post(f"{BASE_URL}/authority/employees", headers=headers, json=field_data)
            if response.status_code == 200:
                employee = response.json()
                field_employee_id = employee.get("id")
                self.created_employees.append({"id": field_employee_id, "email": field_data["email"], "password": field_data["password"], "type": "field"})
                self.log_test("Create Field Employee", True, f"Created field employee: {field_employee_id}")
            else:
                self.log_test("Create Field Employee", False, f"Failed: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Create Field Employee", False, f"Exception: {str(e)}")
            return False
        
        # Create yard employee
        try:
            yard_data = {
                "email": f"yard.test.{int(time.time())}@test.de",
                "password": "YardTest123!",
                "name": "Yard Test Employee",
                "sub_role": "yard"
            }
            response = requests.post(f"{BASE_URL}/authority/employees", headers=headers, json=yard_data)
            if response.status_code == 200:
                employee = response.json()
                yard_employee_id = employee.get("id")
                self.created_employees.append({"id": yard_employee_id, "email": yard_data["email"], "password": yard_data["password"], "type": "yard"})
                self.log_test("Create Yard Employee", True, f"Created yard employee: {yard_employee_id}")
            else:
                self.log_test("Create Yard Employee", False, f"Failed: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Create Yard Employee", False, f"Exception: {str(e)}")
            return False
        
        return True
    
    def authenticate_employees(self):
        """Authenticate the created employees"""
        # Authenticate field employee
        field_employee = next(emp for emp in self.created_employees if emp["type"] == "field")
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={
                    "email": field_employee["email"],
                    "password": field_employee["password"]
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.field_employee_token = data.get("access_token")
                self.log_test("Field Employee Authentication", True, f"Successfully authenticated field employee")
            else:
                self.log_test("Field Employee Authentication", False, f"Failed: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Field Employee Authentication", False, f"Exception: {str(e)}")
            return False
        
        # Authenticate yard employee
        yard_employee = next(emp for emp in self.created_employees if emp["type"] == "yard")
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={
                    "email": yard_employee["email"],
                    "password": yard_employee["password"]
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.yard_employee_token = data.get("access_token")
                self.log_test("Yard Employee Authentication", True, f"Successfully authenticated yard employee")
            else:
                self.log_test("Yard Employee Authentication", False, f"Failed: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Yard Employee Authentication", False, f"Exception: {str(e)}")
            return False
        
        return True
    
    def create_test_job(self):
        """Create a test job for authority release testing"""
        headers = {"Authorization": f"Bearer {self.authority_token}"}
        
        try:
            job_data = {
                "license_plate": "ROLE-TEST-001",
                "tow_reason": "Role-based access test",
                "location_address": "Teststraße 789, Hamburg",
                "location_lat": 53.5511,
                "location_lng": 9.9937,
                "target_yard": "authority_yard",
                "authority_yard_id": "yard-001",
                "authority_yard_name": "Test Authority Yard",
                "authority_yard_address": "Authority Yard Address",
                "authority_price_category_id": "cat-001",
                "authority_base_price": 150.0,
                "authority_daily_rate": 25.0
            }
            response = requests.post(f"{BASE_URL}/jobs", headers=headers, json=job_data)
            if response.status_code == 200:
                job = response.json()
                self.test_job_id = job.get("id")
                
                # Update job to delivered_to_authority status
                update_data = {"status": "delivered_to_authority"}
                requests.patch(f"{BASE_URL}/jobs/{self.test_job_id}", headers=headers, json=update_data)
                
                self.log_test("Create Test Job", True, f"Created test job: {self.test_job_id}")
                return True
            else:
                self.log_test("Create Test Job", False, f"Failed: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Create Test Job", False, f"Exception: {str(e)}")
            return False
    
    def test_field_employee_access_restriction(self):
        """Test that field employee cannot release vehicles"""
        headers = {"Authorization": f"Bearer {self.field_employee_token}"}
        
        release_data = {
            "owner_first_name": "Test",
            "owner_last_name": "Field",
            "owner_address": "Test Address",
            "payment_method": "cash",
            "payment_amount": 175.0
        }
        
        try:
            response = requests.post(f"{BASE_URL}/jobs/{self.test_job_id}/authority-release", headers=headers, json=release_data)
            if response.status_code == 403:
                error_detail = response.json().get("detail", "")
                if "Außendienst-Mitarbeiter" in error_detail or "Hof-Mitarbeiter" in error_detail:
                    self.log_test("Field Employee Access Restriction", True, 
                                f"Field employee correctly denied access: {error_detail}")
                else:
                    self.log_test("Field Employee Access Restriction", True, 
                                f"Field employee denied access (403): {error_detail}")
            else:
                self.log_test("Field Employee Access Restriction", False, 
                            f"Field employee should be denied access but got status: {response.status_code}")
        except Exception as e:
            self.log_test("Field Employee Access Restriction", False, f"Exception: {str(e)}")
    
    def test_yard_employee_access_allowed(self):
        """Test that yard employee can release vehicles"""
        headers = {"Authorization": f"Bearer {self.yard_employee_token}"}
        
        release_data = {
            "owner_first_name": "Test",
            "owner_last_name": "Yard",
            "owner_address": "Test Address",
            "payment_method": "cash",
            "payment_amount": 175.0
        }
        
        try:
            response = requests.post(f"{BASE_URL}/jobs/{self.test_job_id}/authority-release", headers=headers, json=release_data)
            if response.status_code == 200:
                self.log_test("Yard Employee Access Allowed", True, 
                            f"Yard employee successfully released vehicle")
            elif response.status_code == 400 and "bereits freigegeben" in response.json().get("detail", ""):
                self.log_test("Yard Employee Access Allowed", True, 
                            f"Yard employee has access (vehicle already released)")
            else:
                self.log_test("Yard Employee Access Allowed", False, 
                            f"Yard employee should have access but got status: {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Yard Employee Access Allowed", False, f"Exception: {str(e)}")
    
    def cleanup(self):
        """Clean up created test data"""
        print("\n" + "=" * 50)
        print("CLEANING UP TEST DATA")
        print("=" * 50)
        
        headers = {"Authorization": f"Bearer {self.authority_token}"}
        
        # Delete created employees
        for employee in self.created_employees:
            try:
                response = requests.delete(f"{BASE_URL}/authority/employees/{employee['id']}", headers=headers)
                if response.status_code == 200:
                    print(f"✅ Deleted {employee['type']} employee {employee['id']}")
                else:
                    print(f"⚠️  Could not delete {employee['type']} employee {employee['id']}: {response.status_code}")
            except Exception as e:
                print(f"❌ Error deleting {employee['type']} employee {employee['id']}: {str(e)}")
    
    def run_test(self):
        """Run the role-based access test"""
        print("=" * 80)
        print("ROLE-BASED ACCESS TEST FOR AUTHORITY RELEASE")
        print("=" * 80)
        
        # Setup
        if not self.authenticate_authority():
            return
        
        if not self.create_test_employees():
            return
        
        if not self.authenticate_employees():
            return
        
        if not self.create_test_job():
            return
        
        print("\n" + "=" * 50)
        print("TESTING ROLE-BASED ACCESS RESTRICTIONS")
        print("=" * 50)
        
        # Test access restrictions
        self.test_field_employee_access_restriction()
        self.test_yard_employee_access_allowed()
        
        # Cleanup
        self.cleanup()
        
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
    tester = RoleBasedAccessTester()
    tester.run_test()
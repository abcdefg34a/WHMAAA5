#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class NewFeaturesAPITester:
    def __init__(self, base_url="https://vehicle-recovery-7.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.authority_token = None
        self.towing_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # Generate unique identifiers for this test run
        timestamp = datetime.now().strftime('%H%M%S')
        
        # Test credentials from review request
        self.authority_creds = {
            "email": "behoerde@test.de",
            "password": "Behoerde123"
        }
        
        self.towing_creds = {
            "email": "abschlepp@test.de", 
            "password": "Abschlepp123"
        }
        
        # Unique test data for this run
        self.unique_license_plate = f"DUP-TEST{timestamp}"
        self.unique_employee_email = f"test-employee-{timestamp}@test.de"

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

    def login_users(self):
        """Login with provided test credentials"""
        print("\n🔐 Logging in with provided test credentials...")
        
        # Login as Authority
        success, response = self.run_test(
            "Authority Login", "POST", "auth/login", 200, self.authority_creds
        )
        
        if success and 'access_token' in response:
            self.authority_token = response['access_token']
            print(f"   ✅ Authority login successful")
        else:
            print(f"   ❌ Authority login failed")
            return False
        
        # Login as Towing Service
        success, response = self.run_test(
            "Towing Service Login", "POST", "auth/login", 200, self.towing_creds
        )
        
        if success and 'access_token' in response:
            self.towing_token = response['access_token']
            self.towing_service_id = response.get('user', {}).get('id')
            print(f"   ✅ Towing service login successful")
            print(f"   Towing Service ID: {self.towing_service_id}")
        else:
            print(f"   ❌ Towing service login failed")
            return False
        
        return True

    def test_duplicate_license_plate_check(self):
        """TEST 1: Duplicate License Plate Check"""
        print("\n" + "="*60)
        print("TEST 1: DUPLICATE LICENSE PLATE CHECK")
        print("="*60)
        
        if not self.authority_token:
            print("❌ No authority token available")
            return False
        
        license_plate = self.unique_license_plate
        
        # Step 1: Create first job with license plate "DUP-TEST 123"
        job_data_1 = {
            "license_plate": license_plate,
            "vin": "WVWZZZ3CZWE111111",
            "tow_reason": "Parken im Halteverbot",
            "location_address": "Teststraße 1, 12345 Berlin",
            "location_lat": 52.520008,
            "location_lng": 13.404954,
            "notes": "First job for duplicate test"
        }
        
        success, response = self.run_test(
            "Create First Job (DUP-TEST 123)", "POST", "jobs", 200,
            job_data_1, self.authority_token
        )
        
        if not success:
            print("❌ Failed to create first job - cannot continue duplicate test")
            return False
        
        first_job_id = response.get('id')
        print(f"   ✅ First job created successfully with ID: {first_job_id}")
        
        # Step 2: Try to create ANOTHER job with the same license plate
        job_data_2 = {
            "license_plate": license_plate,
            "vin": "WVWZZZ3CZWE222222", 
            "tow_reason": "Falschparker",
            "location_address": "Andere Straße 2, 12345 Berlin",
            "location_lat": 52.521008,
            "location_lng": 13.405954,
            "notes": "Second job for duplicate test - should fail"
        }
        
        success, response = self.run_test(
            "Create Second Job (Same License Plate)", "POST", "jobs", 400,
            job_data_2, self.authority_token
        )
        
        if success:
            # Check if error message is correct
            error_detail = response.get('detail', '')
            expected_message = "Ein Fahrzeug mit diesem Kennzeichen"
            
            if expected_message in error_detail:
                print(f"   ✅ Correct error message received: {error_detail}")
                return True
            else:
                print(f"   ❌ Incorrect error message: {error_detail}")
                return False
        else:
            print("   ❌ Second job creation should have failed with 400 status")
            return False

    def test_edit_job_data_endpoint(self):
        """TEST 2: Edit Job Data Endpoint"""
        print("\n" + "="*60)
        print("TEST 2: EDIT JOB DATA ENDPOINT")
        print("="*60)
        
        if not self.towing_token or not self.towing_service_id:
            print("❌ No towing service token available")
            return False
        
        # Step 1: Create a test job assigned to this towing service
        print("   Creating a test job assigned to towing service...")
        
        job_data = {
            "license_plate": "EDIT-TEST123",
            "vin": "WVWZZZ3CZWE333333",
            "tow_reason": "Test job for editing",
            "location_address": "Edit Straße 1, 12345 Berlin",
            "location_lat": 52.520008,
            "location_lng": 13.404954,
            "notes": "Job for edit test",
            "assigned_service_id": self.towing_service_id
        }
        
        success, response = self.run_test(
            "Create Job for Edit Test", "POST", "jobs", 200,
            job_data, self.authority_token
        )
        
        if not success:
            print("❌ Failed to create test job")
            return False
        
        editable_job = response
        print(f"   ✅ Created test job with ID: {editable_job.get('id')}")
        
        job_id = editable_job.get('id')
        original_license_plate = editable_job.get('license_plate')
        original_vin = editable_job.get('vin')
        original_tow_reason = editable_job.get('tow_reason')
        
        print(f"   Using job ID: {job_id}")
        print(f"   Original license plate: {original_license_plate}")
        print(f"   Original VIN: {original_vin}")
        print(f"   Original tow reason: {original_tow_reason}")
        
        # Step 2: Use the NEW endpoint PATCH /api/jobs/{job_id}/edit-data
        edit_data = {
            "license_plate": "EDITED-123",
            "vin": "WBA12345678901234",
            "tow_reason": "Parken im Parkverbot"
        }
        
        success, response = self.run_test(
            "Edit Job Data", "PATCH", f"jobs/{job_id}/edit-data", 200,
            edit_data, self.towing_token
        )
        
        if not success:
            print("❌ Failed to edit job data")
            return False
        
        print(f"   ✅ Job data edited successfully")
        
        # Step 3: Verify the job data was updated
        success, response = self.run_test(
            "Verify Job Data Updated", "GET", f"jobs/{job_id}", 200,
            token=self.towing_token
        )
        
        if success and response:
            updated_license_plate = response.get('license_plate')
            updated_vin = response.get('vin')
            updated_tow_reason = response.get('tow_reason')
            
            print(f"   Updated license plate: {updated_license_plate}")
            print(f"   Updated VIN: {updated_vin}")
            print(f"   Updated tow reason: {updated_tow_reason}")
            
            # Verify changes
            if (updated_license_plate == "EDITED-123" and 
                updated_vin == "WBA12345678901234" and 
                updated_tow_reason == "Parken im Parkverbot"):
                print(f"   ✅ Job data correctly updated")
            else:
                print(f"   ❌ Job data not correctly updated")
                return False
        
        # Step 4: Test editing a job with "released" status (should fail)
        # First, try to find a released job or create one
        released_job_id = None
        
        # Try to update our test job to released status first
        release_data = {"status": "released"}
        success, response = self.run_test(
            "Update Job to Released", "PATCH", f"jobs/{job_id}", 200,
            release_data, self.towing_token
        )
        
        if success:
            released_job_id = job_id
            print(f"   ✅ Job updated to released status")
        
        if released_job_id:
            # Try to edit the released job (should fail)
            edit_data_released = {
                "license_plate": "SHOULD-FAIL",
                "vin": "SHOULDFAIL123456",
                "tow_reason": "This should fail"
            }
            
            success, response = self.run_test(
                "Edit Released Job (Should Fail)", "PATCH", f"jobs/{released_job_id}/edit-data", 400,
                edit_data_released, self.towing_token
            )
            
            if success:
                print(f"   ✅ Correctly prevented editing of released job")
            else:
                print(f"   ❌ Should have prevented editing of released job")
                return False
        
        # Step 5: Check audit log for edit action
        # Note: This would require admin access to check audit logs
        print(f"   ✅ Edit job data endpoint test completed successfully")
        
        return True

    def test_employee_email_uniqueness(self):
        """TEST 3: Employee Email Uniqueness"""
        print("\n" + "="*60)
        print("TEST 3: EMPLOYEE EMAIL UNIQUENESS")
        print("="*60)
        
        if not self.authority_token:
            print("❌ No authority token available")
            return False
        
        test_email = "test-employee@test.de"
        
        # Step 1: Create first employee with email "test-employee@test.de"
        employee_data_1 = {
            "email": test_email,
            "password": "TestEmployee123!",
            "name": "Test Employee 1"
        }
        
        success, response = self.run_test(
            "Create First Employee", "POST", "authority/employees", 200,
            employee_data_1, self.authority_token
        )
        
        if not success:
            print("❌ Failed to create first employee")
            return False
        
        first_employee_id = response.get('id')
        print(f"   ✅ First employee created successfully with ID: {first_employee_id}")
        print(f"   Employee email: {response.get('email')}")
        print(f"   Employee name: {response.get('name')}")
        print(f"   Dienstnummer: {response.get('dienstnummer')}")
        
        # Step 2: Try to create ANOTHER employee with the same email
        employee_data_2 = {
            "email": test_email,  # Same email
            "password": "TestEmployee2123!",
            "name": "Test Employee 2"
        }
        
        success, response = self.run_test(
            "Create Second Employee (Same Email)", "POST", "authority/employees", 400,
            employee_data_2, self.authority_token
        )
        
        if success:
            # Check if error message is correct
            error_detail = response.get('detail', '')
            expected_message = "E-Mail bereits registriert"
            
            if expected_message in error_detail:
                print(f"   ✅ Correct error message received: {error_detail}")
                return True
            else:
                print(f"   ❌ Incorrect error message: {error_detail}")
                print(f"   Expected: '{expected_message}'")
                return False
        else:
            print("   ❌ Second employee creation should have failed with 400 status")
            return False

    def run_all_tests(self):
        """Run all new feature tests"""
        print("\n" + "="*80)
        print("BACKEND TESTING: NEW FEATURES")
        print("="*80)
        
        # Login first
        if not self.login_users():
            print("❌ Failed to login - cannot continue tests")
            return False
        
        # Run the three specific tests
        test1_result = self.test_duplicate_license_plate_check()
        test2_result = self.test_edit_job_data_endpoint()
        test3_result = self.test_employee_email_uniqueness()
        
        # Print summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        print(f"Total tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        print(f"\nTest Results:")
        print(f"1. Duplicate License Plate Check: {'✅ PASSED' if test1_result else '❌ FAILED'}")
        print(f"2. Edit Job Data Endpoint: {'✅ PASSED' if test2_result else '❌ FAILED'}")
        print(f"3. Employee Email Uniqueness: {'✅ PASSED' if test3_result else '❌ FAILED'}")
        
        all_passed = test1_result and test2_result and test3_result
        
        if all_passed:
            print(f"\n🎉 ALL NEW FEATURE TESTS PASSED!")
        else:
            print(f"\n⚠️  SOME TESTS FAILED - See details above")
        
        return all_passed

if __name__ == "__main__":
    tester = NewFeaturesAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
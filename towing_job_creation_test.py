#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class TowingJobCreationTester:
    def __init__(self, base_url="https://react-state-sync.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.authority_token = None
        self.towing_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # Use provided test credentials from review request
        self.admin_credentials = {
            "email": "admin@test.de",
            "password": "Admin123!"
        }
        
        self.towing_credentials = {
            "email": "abschlepp@test.de", 
            "password": "Abschlepp123"
        }
        
        self.authority_credentials = {
            "email": "behoerde@test.de",
            "password": "Behoerde123"
        }

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

    def test_admin_login(self):
        """Step 1: Login as admin"""
        print("\n🔐 Step 1: Admin Login...")
        
        success, response = self.run_test(
            "Admin Login", "POST", "auth/login", 200, self.admin_credentials
        )
        
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            user_data = response.get('user', {})
            print(f"   ✅ Admin login successful")
            print(f"   Admin ID: {user_data.get('id')}")
            print(f"   Admin Role: {user_data.get('role')}")
            return True
        else:
            print(f"   ❌ Admin login failed")
            return False

    def test_sync_links(self):
        """Step 2: Call POST /api/admin/sync-links to synchronize existing authority-service links"""
        print("\n🔄 Step 2: Synchronizing Authority-Service Links...")
        
        if not self.admin_token:
            print("❌ No admin token available")
            return False
        
        success, response = self.run_test(
            "Sync Authority-Service Links", "POST", "admin/sync-links", 200,
            {}, self.admin_token
        )
        
        if success and response:
            updated_count = response.get('updated_count', 0)
            message = response.get('message', '')
            print(f"   ✅ Sync completed: {message}")
            print(f"   Updated {updated_count} links")
            return True
        else:
            print(f"   ❌ Sync failed")
            return False

    def test_towing_login(self):
        """Step 3: Login as towing service"""
        print("\n🚛 Step 3: Towing Service Login...")
        
        success, response = self.run_test(
            "Towing Service Login", "POST", "auth/login", 200, self.towing_credentials
        )
        
        if success and 'access_token' in response:
            self.towing_token = response['access_token']
            user_data = response.get('user', {})
            self.towing_service_id = user_data.get('id')
            self.towing_service_code = user_data.get('service_code')
            print(f"   ✅ Towing service login successful")
            print(f"   Service ID: {self.towing_service_id}")
            print(f"   Service Code: {self.towing_service_code}")
            print(f"   Company: {user_data.get('company_name', 'N/A')}")
            return True
        else:
            print(f"   ❌ Towing service login failed")
            return False

    def test_get_linked_authorities(self):
        """Step 4: Call GET /api/towing/linked-authorities to verify linked authorities"""
        print("\n🏛️ Step 4: Getting Linked Authorities...")
        
        if not self.towing_token:
            print("❌ No towing service token available")
            return False, []
        
        success, response = self.run_test(
            "Get Linked Authorities", "GET", "towing/linked-authorities", 200,
            token=self.towing_token
        )
        
        if success:
            linked_authorities = response if isinstance(response, list) else []
            print(f"   ✅ Found {len(linked_authorities)} linked authorities")
            
            for i, authority in enumerate(linked_authorities):
                authority_name = authority.get('authority_name', 'Unknown')
                authority_id = authority.get('id', 'Unknown')
                print(f"   - Authority {i+1}: {authority_name} (ID: {authority_id})")
            
            return True, linked_authorities
        else:
            print(f"   ❌ Failed to get linked authorities")
            return False, []

    def test_authority_login(self):
        """Step 5: Login as authority (if needed for linking)"""
        print("\n🏛️ Step 5: Authority Login...")
        
        success, response = self.run_test(
            "Authority Login", "POST", "auth/login", 200, self.authority_credentials
        )
        
        if success and 'access_token' in response:
            self.authority_token = response['access_token']
            user_data = response.get('user', {})
            self.authority_id = user_data.get('id')
            print(f"   ✅ Authority login successful")
            print(f"   Authority ID: {self.authority_id}")
            print(f"   Authority Name: {user_data.get('authority_name', 'N/A')}")
            return True
        else:
            print(f"   ❌ Authority login failed")
            return False

    def test_link_service(self):
        """Step 6: Link towing service to authority (if no links exist)"""
        print("\n🔗 Step 6: Linking Towing Service to Authority...")
        
        if not self.authority_token or not self.towing_service_code:
            print("❌ Missing authority token or service code")
            return False
        
        link_data = {"service_code": self.towing_service_code}
        success, response = self.run_test(
            "Link Towing Service", "POST", "services/link", 200,
            link_data, self.authority_token
        )
        
        if success and response:
            message = response.get('message', '')
            service_name = response.get('service_name', '')
            print(f"   ✅ Link created: {message}")
            print(f"   Service: {service_name}")
            return True
        else:
            print(f"   ❌ Failed to link service")
            return False

    def test_create_job_as_towing_service(self, authority_id: str):
        """Step 7: Create a job as towing service using POST /api/jobs"""
        print("\n📋 Step 7: Creating Job as Towing Service...")
        
        if not self.towing_token or not authority_id:
            print("❌ Missing towing token or authority ID")
            return False
        
        # Use the exact payload from the review request
        job_data = {
            "for_authority_id": authority_id,
            "license_plate": "B-TEST 999",
            "tow_reason": "Falschparken",
            "location_address": "Teststraße 1, 10115 Berlin",
            "location_lat": 52.52,
            "location_lng": 13.405,
            "job_type": "towing",
            "notes": "Testauftrag vom Abschleppdienst erstellt"
        }
        
        success, response = self.run_test(
            "Create Job as Towing Service", "POST", "jobs", 200,
            job_data, self.towing_token
        )
        
        if success and response:
            job_id = response.get('id')
            job_number = response.get('job_number')
            status = response.get('status')
            authority_id_response = response.get('authority_id')
            created_by_service = response.get('created_by_service')
            assigned_service_id = response.get('assigned_service_id')
            
            print(f"   ✅ Job created successfully")
            print(f"   Job ID: {job_id}")
            print(f"   Job Number: {job_number}")
            print(f"   Status: {status}")
            print(f"   Authority ID: {authority_id_response}")
            print(f"   Created by Service: {created_by_service}")
            print(f"   Assigned Service ID: {assigned_service_id}")
            
            # Verify the job was created with correct properties
            verification_passed = True
            
            if status != "assigned":
                print(f"   ❌ Expected status 'assigned', got '{status}'")
                verification_passed = False
            else:
                print(f"   ✅ Status is correctly 'assigned'")
            
            if authority_id_response != authority_id:
                print(f"   ❌ Expected authority_id '{authority_id}', got '{authority_id_response}'")
                verification_passed = False
            else:
                print(f"   ✅ Authority ID is correct")
            
            if assigned_service_id != self.towing_service_id:
                print(f"   ❌ Expected assigned_service_id '{self.towing_service_id}', got '{assigned_service_id}'")
                verification_passed = False
            else:
                print(f"   ✅ Job is assigned to correct towing service")
            
            if created_by_service != True:
                print(f"   ❌ Expected created_by_service to be True, got '{created_by_service}'")
                verification_passed = False
            else:
                print(f"   ✅ Job correctly marked as created by service")
            
            return verification_passed, job_id
        else:
            print(f"   ❌ Failed to create job")
            return False, None

    def test_verify_job_details(self, job_id: str):
        """Step 8: Verify job details by fetching it"""
        print("\n🔍 Step 8: Verifying Job Details...")
        
        if not job_id or not self.towing_token:
            print("❌ Missing job ID or towing token")
            return False
        
        success, response = self.run_test(
            "Get Job Details", "GET", f"jobs/{job_id}", 200,
            token=self.towing_token
        )
        
        if success and response:
            print(f"   ✅ Job details retrieved successfully")
            print(f"   License Plate: {response.get('license_plate')}")
            print(f"   Tow Reason: {response.get('tow_reason')}")
            print(f"   Location: {response.get('location_address')}")
            print(f"   Job Type: {response.get('job_type')}")
            print(f"   Notes: {response.get('notes')}")
            print(f"   Created At: {response.get('created_at')}")
            print(f"   Accepted At: {response.get('accepted_at')}")
            
            # Verify accepted_at is set (should be auto-accepted for service-created jobs)
            accepted_at = response.get('accepted_at')
            if accepted_at:
                print(f"   ✅ Job is auto-accepted (accepted_at: {accepted_at})")
            else:
                print(f"   ❌ Job is not auto-accepted (missing accepted_at)")
            
            return True
        else:
            print(f"   ❌ Failed to get job details")
            return False

    def run_towing_job_creation_test(self):
        """Run the complete towing service job creation test as specified in review request"""
        print("🚀 Starting Towing Service Job Creation Test...")
        print(f"📡 Testing against: {self.base_url}")
        print("="*80)
        
        try:
            # Step 1: Login as admin
            if not self.test_admin_login():
                print("❌ CRITICAL: Admin login failed - stopping test")
                return False
            
            # Step 2: Sync existing authority-service links
            if not self.test_sync_links():
                print("❌ CRITICAL: Link synchronization failed - stopping test")
                return False
            
            # Step 3: Login as towing service
            if not self.test_towing_login():
                print("❌ CRITICAL: Towing service login failed - stopping test")
                return False
            
            # Step 4: Get linked authorities
            linked_success, linked_authorities = self.test_get_linked_authorities()
            if not linked_success:
                print("❌ CRITICAL: Failed to get linked authorities - stopping test")
                return False
            
            # Step 5: If no linked authorities, create a link
            if not linked_authorities:
                print("\n⚠️ No linked authorities found - creating link...")
                
                # Login as authority
                if not self.test_authority_login():
                    print("❌ CRITICAL: Authority login failed - stopping test")
                    return False
                
                # Link the service
                if not self.test_link_service():
                    print("❌ CRITICAL: Service linking failed - stopping test")
                    return False
                
                # Get linked authorities again
                linked_success, linked_authorities = self.test_get_linked_authorities()
                if not linked_success or not linked_authorities:
                    print("❌ CRITICAL: Still no linked authorities after linking - stopping test")
                    return False
            
            # Step 6: Use the first linked authority to create a job
            authority_id = linked_authorities[0].get('id')
            authority_name = linked_authorities[0].get('authority_name')
            
            print(f"\n🎯 Using Authority: {authority_name} (ID: {authority_id})")
            
            # Step 7: Create job as towing service
            job_success, job_id = self.test_create_job_as_towing_service(authority_id)
            if not job_success:
                print("❌ CRITICAL: Job creation failed - stopping test")
                return False
            
            # Step 8: Verify job details
            if not self.test_verify_job_details(job_id):
                print("❌ Job verification failed")
                return False
            
            print("\n" + "="*80)
            print("🎉 TOWING SERVICE JOB CREATION TEST COMPLETED SUCCESSFULLY!")
            print("="*80)
            print(f"✅ All {self.tests_passed}/{self.tests_run} tests passed")
            print(f"✅ Job created with ID: {job_id}")
            print(f"✅ Job status: assigned")
            print(f"✅ Job assigned to correct authority: {authority_name}")
            print(f"✅ Job auto-assigned to towing service")
            
            return True
            
        except Exception as e:
            print(f"❌ CRITICAL ERROR: {str(e)}")
            return False

    def print_summary(self):
        """Print test summary"""
        print(f"\n📊 Test Summary:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        if self.test_results:
            failed_tests = [r for r in self.test_results if not r['success']]
            if failed_tests:
                print(f"\n❌ Failed Tests:")
                for test in failed_tests:
                    print(f"   - {test['test']}: {test.get('error', 'Unknown error')}")

if __name__ == "__main__":
    tester = TowingJobCreationTester()
    success = tester.run_towing_job_creation_test()
    tester.print_summary()
    
    sys.exit(0 if success else 1)
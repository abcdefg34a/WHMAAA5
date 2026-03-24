#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
import random
import string

class ReviewRequestTester:
    def __init__(self, base_url="https://cost-automation.preview.emergentagent.com/api"):
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
        
        # Generate unique test data
        timestamp = datetime.now().strftime("%H%M%S")
        self.test_job_data = {
            "license_plate": f"B-REV{timestamp}",
            "vin": f"WVWZZZ3CZWE{timestamp}",
            "tow_reason": "Parken im Halteverbot - Review Test",
            "location_address": "Alte Adresse, 12345 Berlin",
            "location_lat": 52.520008,
            "location_lng": 13.404954,
            "notes": "Review request test job"
        }
        
        self.test_job_id = None

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

    def test_1_login_all_users(self):
        """1. Login all 3 users (admin, authority, towing)"""
        print("\n🎯 REVIEW REQUEST TEST 1: Login all 3 users")
        
        # Admin login
        success, response, status, error = self.run_test(
            "1a. Admin Login", "POST", "auth/login", 200, self.admin_creds
        )
        
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            print(f"   ✅ Admin token obtained")
        else:
            return False
        
        # Authority login
        success, response, status, error = self.run_test(
            "1b. Authority Login", "POST", "auth/login", 200, self.authority_creds
        )
        
        if success and 'access_token' in response:
            self.authority_token = response['access_token']
            print(f"   ✅ Authority token obtained")
        else:
            return False
        
        # Towing service login
        success, response, status, error = self.run_test(
            "1c. Towing Service Login", "POST", "auth/login", 200, self.towing_creds
        )
        
        if success and 'access_token' in response:
            self.towing_token = response['access_token']
            print(f"   ✅ Towing service token obtained")
            return True
        else:
            return False

    def test_2_create_job_as_authority(self):
        """2. Create job as authority"""
        print("\n🎯 REVIEW REQUEST TEST 2: Create job as authority")
        
        if not self.authority_token:
            print("❌ No authority token available")
            return False
            
        success, response, status, error = self.run_test(
            "2. Create Job as Authority", "POST", "jobs", 200, 
            self.test_job_data, self.authority_token
        )
        
        if success and 'id' in response:
            self.test_job_id = response['id']
            print(f"   ✅ Job created with ID: {self.test_job_id}")
            print(f"   ✅ License plate: {response.get('license_plate')}")
            print(f"   ✅ Job number: {response.get('job_number')}")
            return True
        
        return False

    def test_3_edit_job_with_location_change(self):
        """3. Edit job with location change"""
        print("\n🎯 REVIEW REQUEST TEST 3: Edit job with location change")
        
        if not self.test_job_id or not self.authority_token:
            print("❌ No job ID or authority token available")
            return False
            
        edit_data = {
            "license_plate": f"B-EDIT{datetime.now().strftime('%H%M%S')}",
            "location_address": "Neue Adresse, 54321 Hamburg",
            "location_lat": 53.5511,
            "location_lng": 9.9937,
            "notes": "Location updated via review test"
        }
        
        success, response, status, error = self.run_test(
            "3. Edit Job with Location Change", "PATCH", 
            f"jobs/{self.test_job_id}/edit-data", 200, 
            edit_data, self.authority_token
        )
        
        if success:
            print(f"   ✅ Job location updated successfully")
            print(f"   ✅ New address: {edit_data['location_address']}")
            print(f"   ✅ New coordinates: {edit_data['location_lat']}, {edit_data['location_lng']}")
        
        return success

    def test_4_delete_job(self):
        """4. Delete job"""
        print("\n🎯 REVIEW REQUEST TEST 4: Delete job")
        
        if not self.test_job_id or not self.authority_token:
            print("❌ No job ID or authority token available")
            return False
            
        success, response, status, error = self.run_test(
            "4. Delete Job", "DELETE", f"jobs/{self.test_job_id}", 200, 
            token=self.authority_token
        )
        
        if success:
            print(f"   ✅ Job {self.test_job_id} deleted successfully")
            
            # Verify deletion by trying to get the job
            verify_success, verify_response, verify_status, verify_error = self.run_test(
                "4b. Verify Job Deletion", "GET", f"jobs/{self.test_job_id}", 404,
                token=self.authority_token
            )
            
            if verify_success:
                print(f"   ✅ Job deletion verified - returns 404 as expected")
            
        return success

    def test_5_pdf_download(self):
        """5. PDF download"""
        print("\n🎯 REVIEW REQUEST TEST 5: PDF download")
        
        if not self.authority_token:
            print("❌ No authority token available")
            return False
        
        # Create a new job for PDF testing
        timestamp = datetime.now().strftime("%H%M%S")
        pdf_job_data = {
            "license_plate": f"B-PDF{timestamp}",
            "vin": f"WVWZZZ3CZWE{timestamp}",
            "tow_reason": "PDF test job",
            "location_address": "PDF Teststraße 1, 12345 Berlin",
            "location_lat": 52.520008,
            "location_lng": 13.404954,
            "notes": "Job for PDF generation test"
        }
        
        success, response, status, error = self.run_test(
            "5a. Create Job for PDF", "POST", "jobs", 200, 
            pdf_job_data, self.authority_token
        )
        
        if not success or 'id' not in response:
            print("❌ Failed to create job for PDF test")
            return False
            
        pdf_job_id = response['id']
        
        # Test PDF generation
        url = f"{self.base_url}/jobs/{pdf_job_id}/pdf"
        headers = {'Authorization': f'Bearer {self.authority_token}'}
        
        try:
            print(f"   GET {url}")
            response = requests.get(url, headers=headers, timeout=30)
            
            success = response.status_code == 200
            content_type = response.headers.get('content-type', '')
            
            if success and 'application/pdf' in content_type:
                print(f"✅ PASSED - Status: {response.status_code}")
                print(f"   ✅ Content-Type: {content_type}")
                print(f"   ✅ PDF size: {len(response.content)} bytes")
                self.tests_passed += 1
                return True
            else:
                error_msg = f"Expected PDF, got status {response.status_code}, content-type: {content_type}"
                print(f"❌ FAILED - {error_msg}")
                self.failed_tests.append({
                    'test': '5. PDF Download',
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
                'test': '5. PDF Download',
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

    def test_6_public_vehicle_search_with_cost_breakdown(self):
        """6. Public vehicle search with cost breakdown"""
        print("\n🎯 REVIEW REQUEST TEST 6: Public vehicle search with cost breakdown")
        
        # Search for a vehicle that might exist
        success, response, status, error = self.run_test(
            "6. Public Vehicle Search", "GET", "search/vehicle?q=B-TEST", 200
        )
        
        if success and isinstance(response, dict):
            found = response.get('found', False)
            print(f"   ✅ Search completed - Found: {found}")
            
            if found:
                print(f"   ✅ Job Number: {response.get('job_number', 'N/A')}")
                print(f"   ✅ License Plate: {response.get('license_plate', 'N/A')}")
                print(f"   ✅ Status: {response.get('status', 'N/A')}")
                print(f"   ✅ Tow Cost: {response.get('tow_cost', 'N/A')}€")
                print(f"   ✅ Daily Cost: {response.get('daily_cost', 'N/A')}€")
                print(f"   ✅ Total Cost: {response.get('total_cost', 'N/A')}€")
                print(f"   ✅ Location Lat: {response.get('location_lat', 'N/A')}")
                print(f"   ✅ Location Lng: {response.get('location_lng', 'N/A')}")
            else:
                print(f"   ✅ No vehicle found (expected for test data)")
        
        return success

    def test_7_pricing_settings_update(self):
        """7. Pricing settings update (as towing service)"""
        print("\n🎯 REVIEW REQUEST TEST 7: Pricing settings update (as towing service)")
        
        if not self.towing_token:
            print("❌ No towing service token available")
            return False
            
        pricing_data = {
            "time_based_enabled": True,
            "first_half_hour": 150.00,
            "additional_half_hour": 100.00,
            "processing_fee": 35.00,
            "empty_trip_fee": 55.00
        }
        
        success, response, status, error = self.run_test(
            "7. Update Pricing Settings", "PATCH", "services/pricing-settings", 200, 
            pricing_data, self.towing_token
        )
        
        if success:
            print(f"   ✅ Pricing settings updated successfully")
            print(f"   ✅ Time-based enabled: {pricing_data['time_based_enabled']}")
            print(f"   ✅ First half hour: {pricing_data['first_half_hour']}€")
            print(f"   ✅ Additional half hour: {pricing_data['additional_half_hour']}€")
        
        return success

    def test_8_excel_export(self):
        """8. Excel export"""
        print("\n🎯 REVIEW REQUEST TEST 8: Excel export")
        
        if not self.admin_token:
            print("❌ No admin token available")
            return False
            
        url = f"{self.base_url}/export/jobs/excel"
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            print(f"   GET {url}")
            response = requests.get(url, headers=headers, timeout=30)
            
            success = response.status_code == 200
            content_type = response.headers.get('content-type', '')
            
            if success and ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in content_type or 
                           'application/octet-stream' in content_type):
                print(f"✅ PASSED - Status: {response.status_code}")
                print(f"   ✅ Content-Type: {content_type}")
                print(f"   ✅ Excel file size: {len(response.content)} bytes")
                self.tests_passed += 1
                return True
            else:
                error_msg = f"Expected Excel file, got status {response.status_code}, content-type: {content_type}"
                print(f"❌ FAILED - {error_msg}")
                self.failed_tests.append({
                    'test': '8. Excel Export',
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
                'test': '8. Excel Export',
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

    def test_9_admin_stats(self):
        """9. Admin stats"""
        print("\n🎯 REVIEW REQUEST TEST 9: Admin stats")
        
        if not self.admin_token:
            print("❌ No admin token available")
            return False
            
        success, response, status, error = self.run_test(
            "9. Admin Stats", "GET", "admin/stats", 200, token=self.admin_token
        )
        
        if success and isinstance(response, dict):
            print(f"   ✅ Total Jobs: {response.get('total_jobs', 'N/A')}")
            print(f"   ✅ Pending Jobs: {response.get('pending_jobs', 'N/A')}")
            print(f"   ✅ In Yard Jobs: {response.get('in_yard_jobs', 'N/A')}")
            print(f"   ✅ Released Jobs: {response.get('released_jobs', 'N/A')}")
            print(f"   ✅ Total Services: {response.get('total_services', 'N/A')}")
            print(f"   ✅ Total Authorities: {response.get('total_authorities', 'N/A')}")
        
        return success

    def test_10_forgot_password(self):
        """10. Forgot password"""
        print("\n🎯 REVIEW REQUEST TEST 10: Forgot password")
        
        forgot_data = {"email": "admin@test.de"}
        
        success, response, status, error = self.run_test(
            "10. Forgot Password", "POST", "auth/forgot-password", 200, forgot_data
        )
        
        if success and isinstance(response, dict):
            message = response.get('message', '')
            print(f"   ✅ Response message: {message}")
        
        return success

    def run_review_tests(self):
        """Run all 10 critical tests from review request"""
        print("🎯 STARTING REVIEW REQUEST BACKEND TESTING")
        print("=" * 60)
        print("Testing 10 critical endpoints with provided credentials:")
        print("- Admin: admin@test.de / Admin123!")
        print("- Behörde: test-behoerde@test.de / TestPass123!")
        print("- Abschleppdienst: abschlepp@test.de / Abschlepp123")
        print("=" * 60)
        
        # Run all tests in order
        test_methods = [
            self.test_1_login_all_users,
            self.test_2_create_job_as_authority,
            self.test_3_edit_job_with_location_change,
            self.test_4_delete_job,
            self.test_5_pdf_download,
            self.test_6_public_vehicle_search_with_cost_breakdown,
            self.test_7_pricing_settings_update,
            self.test_8_excel_export,
            self.test_9_admin_stats,
            self.test_10_forgot_password
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
        print("📊 REVIEW REQUEST TEST SUMMARY")
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
        else:
            print("\n🎉 ALL TESTS PASSED! Backend is ready for production.")
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    tester = ReviewRequestTester()
    tester.run_review_tests()
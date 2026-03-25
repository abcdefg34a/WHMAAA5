#!/usr/bin/env python3
"""
Backend Test Suite for New AbschleppPortal Features
Tests the newly implemented features:
1. Authority Yard Job Validation
2. Mark Invoice as Paid functionality
3. Regression testing for existing features
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

class NewFeaturesTest:
    def __init__(self):
        self.admin_token = None
        self.authority_token = None
        self.towing_token = None
        self.authority_user_id = None
        self.towing_service_id = None
        self.test_job_id = None
        self.test_invoice_id = None
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
        
    def make_request(self, method, endpoint, data=None, token=None, expected_status=200):
        """Make HTTP request with error handling"""
        url = f"{API_BASE}{endpoint}"
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "PATCH":
                response = requests.patch(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            print(f"Request: {method} {endpoint} -> Status: {response.status_code}")
            
            if response.status_code != expected_status:
                print(f"Expected status {expected_status}, got {response.status_code}")
                print(f"Response: {response.text}")
                return None, response.status_code
                
            return response.json() if response.content else {}, response.status_code
            
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None, 0

    # ========== AUTHENTICATION TESTS ==========
    
    def test_1_admin_authentication(self):
        """Test 1: Admin Authentication"""
        print("\n=== Test 1: Admin Authentication ===")
        
        response, status = self.make_request(
            "POST", "/auth/login", 
            ADMIN_CREDENTIALS,
            expected_status=200
        )
        
        if response and "access_token" in response:
            self.admin_token = response["access_token"]
            self.log_result("Admin Authentication", True, "Admin login successful")
            return True
        else:
            self.log_result("Admin Authentication", False, f"Login failed with status {status}")
            return False
            
    def test_2_authority_authentication(self):
        """Test 2: Authority Authentication"""
        print("\n=== Test 2: Authority Authentication ===")
        
        response, status = self.make_request(
            "POST", "/auth/login",
            AUTHORITY_CREDENTIALS,
            expected_status=200
        )
        
        if response and "access_token" in response:
            self.authority_token = response["access_token"]
            self.authority_user_id = response["user"]["id"]
            self.log_result("Authority Authentication", True, f"Authority login successful, ID: {self.authority_user_id}")
            return True
        else:
            self.log_result("Authority Authentication", False, f"Login failed with status {status}")
            return False
            
    def test_3_towing_service_authentication(self):
        """Test 3: Towing Service Authentication"""
        print("\n=== Test 3: Towing Service Authentication ===")
        
        response, status = self.make_request(
            "POST", "/auth/login",
            TOWING_SERVICE_CREDENTIALS,
            expected_status=200
        )
        
        if response and "access_token" in response:
            self.towing_token = response["access_token"]
            self.towing_service_id = response["user"]["id"]
            self.log_result("Towing Service Authentication", True, f"Towing service login successful, ID: {self.towing_service_id}")
            return True
        else:
            self.log_result("Towing Service Authentication", False, f"Login failed with status {status}")
            return False

    # ========== AUTHORITY YARD JOB VALIDATION TESTS ==========
    
    def test_4_authority_yard_validation_missing_yard_id(self):
        """Test 4: Authority Yard Job Validation - Missing authority_yard_id"""
        print("\n=== Test 4: Authority Yard Validation - Missing Yard ID ===")
        
        if not self.authority_token:
            self.log_result("Authority Yard Validation - Missing Yard ID", False, "No authority token available")
            return False
            
        # Try to create job with target_yard='authority_yard' but without authority_yard_id
        job_data = {
            "license_plate": f"TEST-{uuid.uuid4().hex[:6].upper()}",
            "tow_reason": "Falschparken",
            "location_address": "Teststraße 123, Hamburg",
            "location_lat": 53.5511,
            "location_lng": 9.9937,
            "target_yard": "authority_yard"
            # Missing authority_yard_id and authority_yard_name
        }
        
        response, status = self.make_request(
            "POST", "/jobs",
            job_data,
            token=self.authority_token,
            expected_status=400
        )
        
        if status == 400 and response and "Bitte wählen Sie einen Behörden-Hof" in response.get("detail", ""):
            self.log_result("Authority Yard Validation - Missing Yard ID", True, 
                          "Correctly rejected job without authority_yard_id")
            return True
        else:
            self.log_result("Authority Yard Validation - Missing Yard ID", False, 
                          f"Expected 400 error with yard selection message, got status {status}")
            return False
            
    def test_5_authority_yard_validation_missing_price_category(self):
        """Test 5: Authority Yard Job Validation - Missing authority_price_category_id"""
        print("\n=== Test 5: Authority Yard Validation - Missing Price Category ===")
        
        if not self.authority_token:
            self.log_result("Authority Yard Validation - Missing Price Category", False, "No authority token available")
            return False
            
        # Try to create job with target_yard='authority_yard' and authority_yard_id but without authority_price_category_id
        job_data = {
            "license_plate": f"TEST-{uuid.uuid4().hex[:6].upper()}",
            "tow_reason": "Falschparken",
            "location_address": "Teststraße 123, Hamburg",
            "location_lat": 53.5511,
            "location_lng": 9.9937,
            "target_yard": "authority_yard",
            "authority_yard_id": "test-yard-id",
            "authority_yard_name": "Test Behörden-Hof"
            # Missing authority_price_category_id
        }
        
        response, status = self.make_request(
            "POST", "/jobs",
            job_data,
            token=self.authority_token,
            expected_status=400
        )
        
        if status == 400 and response and "Bitte wählen Sie eine Preiskategorie" in response.get("detail", ""):
            self.log_result("Authority Yard Validation - Missing Price Category", True, 
                          "Correctly rejected job without authority_price_category_id")
            return True
        else:
            self.log_result("Authority Yard Validation - Missing Price Category", False, 
                          f"Expected 400 error with price category message, got status {status}")
            return False
            
    def test_6_service_yard_job_creation(self):
        """Test 6: Service Yard Job Creation - Should work without authority fields"""
        print("\n=== Test 6: Service Yard Job Creation ===")
        
        if not self.authority_token:
            self.log_result("Service Yard Job Creation", False, "No authority token available")
            return False
            
        # Create job with target_yard='service_yard' - should work without authority fields
        job_data = {
            "license_plate": f"TEST-{uuid.uuid4().hex[:6].upper()}",
            "tow_reason": "Falschparken",
            "location_address": "Teststraße 123, Hamburg",
            "location_lat": 53.5511,
            "location_lng": 9.9937,
            "target_yard": "service_yard",
            "assigned_service_id": self.towing_service_id
        }
        
        response, status = self.make_request(
            "POST", "/jobs",
            job_data,
            token=self.authority_token,
            expected_status=200
        )
        
        if response and "id" in response:
            self.test_job_id = response["id"]
            self.log_result("Service Yard Job Creation", True, 
                          f"Service yard job created successfully, ID: {self.test_job_id}")
            return True
        else:
            self.log_result("Service Yard Job Creation", False, 
                          f"Failed to create service yard job, status {status}")
            return False

    # ========== REGRESSION TESTS ==========
    
    def test_7_get_jobs_list(self):
        """Test 7: GET /api/jobs - List Jobs"""
        print("\n=== Test 7: Get Jobs List ===")
        
        if not self.authority_token:
            self.log_result("Get Jobs List", False, "No authority token available")
            return False
            
        response, status = self.make_request(
            "GET", "/jobs",
            token=self.authority_token,
            expected_status=200
        )
        
        if response and isinstance(response, list):
            self.log_result("Get Jobs List", True, f"Retrieved {len(response)} jobs")
            return True
        else:
            self.log_result("Get Jobs List", False, f"Failed to get jobs list, status {status}")
            return False
            
    def test_8_calculate_costs(self):
        """Test 8: GET /api/jobs/{job_id}/calculate-costs"""
        print("\n=== Test 8: Calculate Costs ===")
        
        if not self.authority_token or not self.test_job_id:
            self.log_result("Calculate Costs", False, "No authority token or test job ID available")
            return False
            
        response, status = self.make_request(
            "GET", f"/jobs/{self.test_job_id}/calculate-costs",
            token=self.authority_token,
            expected_status=200
        )
        
        if response and "total" in response:
            total_cost = response["total"]
            self.log_result("Calculate Costs", True, f"Cost calculation successful, total: €{total_cost}")
            return True
        else:
            self.log_result("Calculate Costs", False, f"Failed to calculate costs, status {status}")
            return False

    # ========== INVOICE MARK AS PAID TESTS ==========
    
    def test_9_get_invoices_list(self):
        """Test 9: GET /api/services/invoices - Get invoices list"""
        print("\n=== Test 9: Get Invoices List ===")
        
        if not self.towing_token:
            self.log_result("Get Invoices List", False, "No towing service token available")
            return False
            
        response, status = self.make_request(
            "GET", "/services/invoices",
            token=self.towing_token,
            expected_status=200
        )
        
        if response and "invoices" in response:
            invoices = response["invoices"]
            # Look for a pending invoice to test with
            pending_invoices = [inv for inv in invoices if inv.get("status") != "paid"]
            if pending_invoices:
                self.test_invoice_id = pending_invoices[0]["id"]
                self.log_result("Get Invoices List", True, 
                              f"Retrieved {len(invoices)} invoices, found pending invoice: {self.test_invoice_id}")
            else:
                self.log_result("Get Invoices List", True, 
                              f"Retrieved {len(invoices)} invoices, but no pending invoices found")
            return True
        else:
            self.log_result("Get Invoices List", False, f"Failed to get invoices list, status {status}")
            return False
            
    def test_10_mark_invoice_as_paid(self):
        """Test 10: PATCH /api/services/invoices/{invoice_id}/mark-paid"""
        print("\n=== Test 10: Mark Invoice as Paid ===")
        
        if not self.towing_token:
            self.log_result("Mark Invoice as Paid", False, "No towing service token available")
            return False
            
        if not self.test_invoice_id:
            self.log_result("Mark Invoice as Paid", False, "No pending invoice available for testing")
            return False
            
        response, status = self.make_request(
            "PATCH", f"/services/invoices/{self.test_invoice_id}/mark-paid",
            token=self.towing_token,
            expected_status=200
        )
        
        if response and response.get("success"):
            self.log_result("Mark Invoice as Paid", True, 
                          f"Invoice {self.test_invoice_id} marked as paid successfully")
            return True
        else:
            self.log_result("Mark Invoice as Paid", False, 
                          f"Failed to mark invoice as paid, status {status}")
            return False
            
    def test_11_mark_already_paid_invoice(self):
        """Test 11: Try to mark already paid invoice - should return 400 error"""
        print("\n=== Test 11: Mark Already Paid Invoice ===")
        
        if not self.towing_token or not self.test_invoice_id:
            self.log_result("Mark Already Paid Invoice", False, "No towing service token or invoice ID available")
            return False
            
        # Try to mark the same invoice as paid again
        response, status = self.make_request(
            "PATCH", f"/services/invoices/{self.test_invoice_id}/mark-paid",
            token=self.towing_token,
            expected_status=400
        )
        
        if status == 400 and response and "bereits als bezahlt markiert" in response.get("detail", ""):
            self.log_result("Mark Already Paid Invoice", True, 
                          "Correctly rejected attempt to mark already paid invoice")
            return True
        else:
            self.log_result("Mark Already Paid Invoice", False, 
                          f"Expected 400 error for already paid invoice, got status {status}")
            return False
            
    def run_all_tests(self):
        """Run all new features tests"""
        print("🚀 Starting AbschleppPortal New Features Tests")
        print(f"Backend URL: {BACKEND_URL}")
        print("=" * 60)
        
        tests = [
            # Authentication tests
            self.test_1_admin_authentication,
            self.test_2_authority_authentication,
            self.test_3_towing_service_authentication,
            
            # Authority yard validation tests
            self.test_4_authority_yard_validation_missing_yard_id,
            self.test_5_authority_yard_validation_missing_price_category,
            self.test_6_service_yard_job_creation,
            
            # Regression tests
            self.test_7_get_jobs_list,
            self.test_8_calculate_costs,
            
            # Invoice mark as paid tests
            self.test_9_get_invoices_list,
            self.test_10_mark_invoice_as_paid,
            self.test_11_mark_already_paid_invoice
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
                
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All new features tests PASSED!")
            return True
        else:
            print(f"⚠️  {total - passed} test(s) FAILED")
            return False

def main():
    """Main test runner"""
    tester = NewFeaturesTest()
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
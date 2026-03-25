#!/usr/bin/env python3
"""
Backend Test Suite for Weight Categories Pricing System
Tests the flexible weight categories pricing system for the German towing app.
"""

import requests
import json
import sys
import os
from datetime import datetime
import uuid

# Get backend URL from environment
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cost-automation.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

# Test credentials
TOWING_SERVICE_CREDENTIALS = {
    "email": "abschlepp@test.de",
    "password": "Abschlepp123!"
}

AUTHORITY_CREDENTIALS = {
    "email": "behoerde@test.de", 
    "password": "Behoerde123!"
}

class WeightCategoriesTest:
    def __init__(self):
        self.towing_token = None
        self.authority_token = None
        self.towing_service_id = None
        self.job_id = None
        self.weight_category_id = None
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
            
    def test_1_towing_service_login(self):
        """Test 1: Towing Service Login"""
        print("\n=== Test 1: Towing Service Login ===")
        
        response, status = self.make_request(
            "POST", "/auth/login", 
            TOWING_SERVICE_CREDENTIALS,
            expected_status=200
        )
        
        if response and "access_token" in response:
            self.towing_token = response["access_token"]
            self.towing_service_id = response["user"]["id"]
            self.log_result("Towing Service Login", True, f"Token received, Service ID: {self.towing_service_id}")
            return True
        else:
            self.log_result("Towing Service Login", False, f"Login failed with status {status}")
            return False
            
    def test_2_save_weight_categories(self):
        """Test 2: Save Weight Categories via PATCH /api/services/pricing-settings"""
        print("\n=== Test 2: Save Weight Categories ===")
        
        if not self.towing_token:
            self.log_result("Save Weight Categories", False, "No towing service token available")
            return False
            
        weight_categories_data = {
            "tow_cost": 150,
            "daily_cost": 25,
            "processing_fee": 50,
            "weight_categories": [
                {
                    "name": "PKW bis 3,5t",
                    "min_weight": None,
                    "max_weight": 3.5,
                    "surcharge": 0,
                    "is_default": True
                },
                {
                    "name": "LKW 3,5-7,5t",
                    "min_weight": 3.5,
                    "max_weight": 7.5,
                    "surcharge": 100
                },
                {
                    "name": "Schwerlast über 7,5t",
                    "min_weight": 7.5,
                    "max_weight": None,
                    "surcharge": 200
                }
            ]
        }
        
        response, status = self.make_request(
            "PATCH", "/services/pricing-settings",
            weight_categories_data,
            token=self.towing_token,
            expected_status=200
        )
        
        if response:
            print(f"Response keys: {list(response.keys())}")
            if "weight_categories" in response:
                weight_categories = response["weight_categories"]
                print(f"Weight categories: {weight_categories}")
                if len(weight_categories) == 3:
                    # Find the LKW category for later use
                    for cat in weight_categories:
                        if cat["name"] == "LKW 3,5-7,5t":
                            self.weight_category_id = cat["id"]
                            break
                            
                    self.log_result("Save Weight Categories", True, 
                                  f"3 weight categories saved successfully. LKW category ID: {self.weight_category_id}")
                    return True
                else:
                    self.log_result("Save Weight Categories", False, 
                                  f"Expected 3 categories, got {len(weight_categories)}")
                    return False
            else:
                self.log_result("Save Weight Categories", False, f"No weight_categories in response. Keys: {list(response.keys())}")
                return False
        else:
            self.log_result("Save Weight Categories", False, f"Failed with status {status}")
            return False
            
    def test_3_authority_login(self):
        """Test 3: Authority Login"""
        print("\n=== Test 3: Authority Login ===")
        
        response, status = self.make_request(
            "POST", "/auth/login",
            AUTHORITY_CREDENTIALS,
            expected_status=200
        )
        
        if response and "access_token" in response:
            self.authority_token = response["access_token"]
            self.log_result("Authority Login", True, "Token received")
            return True
        else:
            self.log_result("Authority Login", False, f"Login failed with status {status}")
            return False
            
    def test_4_fetch_service_weight_categories(self):
        """Test 4: Fetch Service Weight Categories via GET /api/services/{service_id}/weight-categories"""
        print("\n=== Test 4: Fetch Service Weight Categories ===")
        
        if not self.authority_token or not self.towing_service_id:
            self.log_result("Fetch Service Weight Categories", False, "Missing authority token or service ID")
            return False
            
        response, status = self.make_request(
            "GET", f"/services/{self.towing_service_id}/weight-categories",
            token=self.authority_token,
            expected_status=200
        )
        
        if response and "weight_categories" in response:
            weight_categories = response["weight_categories"]
            if len(weight_categories) == 3:
                # Verify the categories
                category_names = [cat["name"] for cat in weight_categories]
                expected_names = ["PKW bis 3,5t", "LKW 3,5-7,5t", "Schwerlast über 7,5t"]
                
                if all(name in category_names for name in expected_names):
                    self.log_result("Fetch Service Weight Categories", True, 
                                  f"Retrieved 3 categories: {category_names}")
                    return True
                else:
                    self.log_result("Fetch Service Weight Categories", False, 
                                  f"Category names mismatch. Got: {category_names}")
                    return False
            else:
                self.log_result("Fetch Service Weight Categories", False, 
                              f"Expected 3 categories, got {len(weight_categories)}")
                return False
        else:
            self.log_result("Fetch Service Weight Categories", False, f"Failed with status {status}")
            return False
            
    def test_5_create_job_with_weight_category(self):
        """Test 5: Create Job with Weight Category"""
        print("\n=== Test 5: Create Job with Weight Category ===")
        
        if not self.authority_token or not self.towing_service_id or not self.weight_category_id:
            self.log_result("Create Job with Weight Category", False, 
                          "Missing authority token, service ID, or weight category ID")
            return False
            
        job_data = {
            "license_plate": "TEST-WEIGHT-001",
            "tow_reason": "Falschparken",
            "location_address": "Teststraße 123, Hamburg",
            "location_lat": 53.5511,
            "location_lng": 9.9937,
            "assigned_service_id": self.towing_service_id,
            "weight_category_id": self.weight_category_id,
            "weight_category_name": "LKW 3,5-7,5t",
            "weight_category_surcharge": 100
        }
        
        response, status = self.make_request(
            "POST", "/jobs",
            job_data,
            token=self.authority_token,
            expected_status=200
        )
        
        if response and "id" in response:
            self.job_id = response["id"]
            job_number = response.get("job_number", "N/A")
            
            # Verify weight category fields are stored
            if (response.get("weight_category_id") == self.weight_category_id and
                response.get("weight_category_name") == "LKW 3,5-7,5t" and
                response.get("weight_category_surcharge") == 100):
                
                self.log_result("Create Job with Weight Category", True, 
                              f"Job created with ID: {self.job_id}, Number: {job_number}")
                return True
            else:
                self.log_result("Create Job with Weight Category", False, 
                              "Weight category fields not properly stored in job")
                return False
        else:
            self.log_result("Create Job with Weight Category", False, f"Failed with status {status}")
            return False
            
    def test_6_calculate_costs(self):
        """Test 6: Calculate Costs with Weight Category Surcharge"""
        print("\n=== Test 6: Calculate Costs ===")
        
        if not self.authority_token or not self.job_id:
            self.log_result("Calculate Costs", False, "Missing authority token or job ID")
            return False
            
        response, status = self.make_request(
            "GET", f"/jobs/{self.job_id}/calculate-costs",
            token=self.authority_token,
            expected_status=200
        )
        
        if response and "breakdown" in response:
            breakdown = response["breakdown"]
            total_cost = response.get("total_cost", 0)
            
            # Look for the weight category surcharge in breakdown
            weight_surcharge_found = False
            for item in breakdown:
                if "LKW 3,5-7,5t" in item.get("label", "") and item.get("amount") == 100:
                    weight_surcharge_found = True
                    break
                    
            if weight_surcharge_found:
                self.log_result("Calculate Costs", True, 
                              f"Weight category surcharge found in breakdown. Total: €{total_cost}")
                return True
            else:
                breakdown_labels = [item.get("label", "") for item in breakdown]
                self.log_result("Calculate Costs", False, 
                              f"Weight category surcharge not found. Breakdown: {breakdown_labels}")
                return False
        else:
            self.log_result("Calculate Costs", False, f"Failed with status {status}")
            return False
            
    def test_7_mongodb_verification(self):
        """Test 7: MongoDB Verification - Check if weight category fields are stored correctly"""
        print("\n=== Test 7: MongoDB Verification ===")
        
        if not self.authority_token or not self.job_id:
            self.log_result("MongoDB Verification", False, "Missing authority token or job ID")
            return False
            
        # Get job details to verify MongoDB storage
        response, status = self.make_request(
            "GET", f"/jobs/{self.job_id}",
            token=self.authority_token,
            expected_status=200
        )
        
        if response:
            # Check if all weight category fields are present and correct
            weight_category_id = response.get("weight_category_id")
            weight_category_name = response.get("weight_category_name")
            weight_category_surcharge = response.get("weight_category_surcharge")
            
            if (weight_category_id == self.weight_category_id and
                weight_category_name == "LKW 3,5-7,5t" and
                weight_category_surcharge == 100):
                
                self.log_result("MongoDB Verification", True, 
                              "All weight category fields stored correctly in MongoDB")
                return True
            else:
                self.log_result("MongoDB Verification", False, 
                              f"Weight category fields incorrect: ID={weight_category_id}, "
                              f"Name={weight_category_name}, Surcharge={weight_category_surcharge}")
                return False
        else:
            self.log_result("MongoDB Verification", False, f"Failed to retrieve job with status {status}")
            return False
            
    def run_all_tests(self):
        """Run all weight categories tests"""
        print("🚀 Starting Weight Categories Pricing System Tests")
        print(f"Backend URL: {BACKEND_URL}")
        print("=" * 60)
        
        tests = [
            self.test_1_towing_service_login,
            self.test_2_save_weight_categories,
            self.test_3_authority_login,
            self.test_4_fetch_service_weight_categories,
            self.test_5_create_job_with_weight_category,
            self.test_6_calculate_costs,
            self.test_7_mongodb_verification
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
            print("🎉 All weight categories tests PASSED!")
            return True
        else:
            print(f"⚠️  {total - passed} test(s) FAILED")
            return False

def main():
    """Main test runner"""
    tester = WeightCategoriesTest()
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
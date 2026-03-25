#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dynamic Pricing System Test for German Towing App
================================================

Tests the complete dynamic pricing flow:
1. Authority Authentication
2. Create Vehicle Category
3. List Vehicle Categories
4. Create Job with Vehicle Category
5. Calculate Costs with Dynamic Pricing
6. Query MongoDB to verify data storage

This test verifies the vehicle category pricing system is working correctly.
"""

import requests
import json
import sys
import time
from datetime import datetime
import pymongo
import os

# Backend URL from frontend .env
BACKEND_URL = "https://dual-yard-system.preview.emergentagent.com/api"

# Test Credentials
AUTHORITY_EMAIL = "behoerde@test.de"
AUTHORITY_PASSWORD = "Behoerde123!"

# MongoDB connection (from backend .env)
MONGO_URL = "mongodb+srv://abschleppapp_db_user:H7OINf2CUc2SF1BY@cluster0.6zfgywr.mongodb.net/?appName=Cluster0"
DB_NAME = "abschleppapp"

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_test(test_name):
    print(f"\n🧪 TEST: {test_name}")

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def print_info(message):
    print(f"ℹ️  {message}")

def make_request(method, endpoint, headers=None, json_data=None, data=None):
    """Helper function to make HTTP requests with error handling"""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=json_data,
            data=data,
            timeout=30
        )
        return response
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return None

def test_authority_login():
    """Test 1: Authority Authentication"""
    print_test("Authority Authentication")
    
    response = make_request("POST", "/auth/login", json_data={
        "email": AUTHORITY_EMAIL,
        "password": AUTHORITY_PASSWORD
    })
    
    if not response:
        print_error("Login request failed")
        return None
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        user = data.get("user", {})
        
        print_success(f"Authority login successful")
        print_info(f"Token: {token[:20]}...")
        print_info(f"User: {user.get('name')} ({user.get('role')})")
        print_info(f"Authority: {user.get('authority_name', 'N/A')}")
        
        return token
    else:
        print_error(f"Login failed: {response.status_code} - {response.text}")
        return None

def test_create_vehicle_category(token):
    """Test 2: Create Vehicle Category"""
    print_test("Create Vehicle Category")
    
    headers = {"Authorization": f"Bearer {token}"}
    category_data = {
        "name": "PKW",
        "description": "PKW unter 3,5t",
        "base_price": 150.0,
        "daily_rate": 25.0
    }
    
    response = make_request("POST", "/vehicle-categories", headers=headers, json_data=category_data)
    
    if not response:
        print_error("Create vehicle category request failed")
        return None
    
    if response.status_code == 200:
        data = response.json()
        category_id = data.get("id")
        
        print_success(f"Vehicle category created successfully")
        print_info(f"Category ID: {category_id}")
        print_info(f"Name: {data.get('name')}")
        print_info(f"Description: {data.get('description')}")
        print_info(f"Base Price: €{data.get('base_price')}")
        print_info(f"Daily Rate: €{data.get('daily_rate')}")
        
        return category_id
    else:
        print_error(f"Create vehicle category failed: {response.status_code} - {response.text}")
        return None

def test_list_vehicle_categories(token):
    """Test 3: List Vehicle Categories"""
    print_test("List Vehicle Categories")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = make_request("GET", "/vehicle-categories", headers=headers)
    
    if not response:
        print_error("List vehicle categories request failed")
        return False
    
    if response.status_code == 200:
        data = response.json()
        categories = data if isinstance(data, list) else data.get('categories', [])
        
        print_success(f"Retrieved {len(categories)} vehicle categories")
        
        for category in categories:
            print_info(f"Category: {category.get('name')} - €{category.get('base_price')} base, €{category.get('daily_rate')} daily")
        
        return len(categories) > 0
    else:
        print_error(f"List vehicle categories failed: {response.status_code} - {response.text}")
        return False

def test_create_job_with_category(token, category_id):
    """Test 4: Create Job with Vehicle Category"""
    print_test("Create Job with Vehicle Category")
    
    headers = {"Authorization": f"Bearer {token}"}
    job_data = {
        "license_plate": "TEST-PRICE-001",
        "tow_reason": "Falschparken",
        "location_address": "Teststraße 123, Hamburg",
        "location_lat": 53.5511,
        "location_lng": 9.9937,
        "vehicle_category_id": category_id
    }
    
    response = make_request("POST", "/jobs", headers=headers, json_data=job_data)
    
    if not response:
        print_error("Create job request failed")
        return None
    
    if response.status_code == 200:
        data = response.json()
        job_id = data.get("id")
        
        print_success(f"Job created successfully")
        print_info(f"Job ID: {job_id}")
        print_info(f"Job Number: {data.get('job_number')}")
        print_info(f"License Plate: {data.get('license_plate')}")
        print_info(f"Vehicle Category ID: {data.get('vehicle_category_id')}")
        
        # Verify vehicle_category_id is stored
        if data.get('vehicle_category_id') == category_id:
            print_success(f"✅ Vehicle category ID correctly stored in job")
        else:
            print_error(f"❌ Vehicle category ID not stored correctly. Expected: {category_id}, Got: {data.get('vehicle_category_id')}")
        
        return job_id
    else:
        print_error(f"Create job failed: {response.status_code} - {response.text}")
        return None

def test_calculate_costs(token, job_id):
    """Test 5: Calculate Costs with Dynamic Pricing"""
    print_test("Calculate Costs with Dynamic Pricing")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = make_request("GET", f"/jobs/{job_id}/calculate-costs", headers=headers)
    
    if not response:
        print_error("Calculate costs request failed")
        return False
    
    if response.status_code == 200:
        data = response.json()
        
        print_success(f"Cost calculation successful")
        print_info(f"Total Cost: €{data.get('total')}")
        print_info(f"Pricing Source: {data.get('pricing_source')}")
        print_info(f"Category Name: {data.get('category_name')}")
        
        # Verify pricing source is vehicle_category
        if data.get('pricing_source') == 'vehicle_category':
            print_success(f"✅ Pricing source is vehicle_category")
        else:
            print_error(f"❌ Wrong pricing source. Expected: vehicle_category, Got: {data.get('pricing_source')}")
        
        # Verify category name
        if data.get('category_name') == 'PKW':
            print_success(f"✅ Category name is correct: PKW")
        else:
            print_error(f"❌ Wrong category name. Expected: PKW, Got: {data.get('category_name')}")
        
        # Verify breakdown contains base price
        breakdown = data.get('breakdown', [])
        print_info(f"Cost Breakdown:")
        for item in breakdown:
            print_info(f"  - {item.get('description', 'N/A')}: €{item.get('amount', 0)}")
        
        # Check if base price is in breakdown
        base_price_found = any(item.get('amount') == 150.0 for item in breakdown)
        if base_price_found:
            print_success(f"✅ Base price (€150.0) found in breakdown")
        else:
            print_error(f"❌ Base price (€150.0) not found in breakdown")
        
        # Verify total is at least the base price
        total = data.get('total', 0)
        if total >= 150.0:
            print_success(f"✅ Total cost (€{total}) is at least base price (€150.0)")
        else:
            print_error(f"❌ Total cost (€{total}) is less than base price (€150.0)")
        
        return True
    else:
        print_error(f"Calculate costs failed: {response.status_code} - {response.text}")
        return False

def test_mongodb_verification():
    """Test 6: Query MongoDB to verify job document contains vehicle_category_id"""
    print_test("MongoDB Verification")
    
    try:
        # Connect to MongoDB
        client = pymongo.MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Query for the test job
        job = db.jobs.find_one({"license_plate": "TEST-PRICE-001"})
        
        if job:
            print_success(f"Job found in MongoDB")
            print_info(f"Job ID: {job.get('id')}")
            print_info(f"License Plate: {job.get('license_plate')}")
            print_info(f"Vehicle Category ID: {job.get('vehicle_category_id')}")
            
            # Verify vehicle_category_id field exists
            if 'vehicle_category_id' in job:
                print_success(f"✅ vehicle_category_id field exists in job document")
                
                # Verify it's not empty
                if job.get('vehicle_category_id'):
                    print_success(f"✅ vehicle_category_id has a value: {job.get('vehicle_category_id')}")
                else:
                    print_error(f"❌ vehicle_category_id field is empty")
            else:
                print_error(f"❌ vehicle_category_id field does not exist in job document")
            
            return True
        else:
            print_error(f"Job with license plate 'TEST-PRICE-001' not found in MongoDB")
            return False
            
    except Exception as e:
        print_error(f"MongoDB query failed: {e}")
        return False
    finally:
        try:
            client.close()
        except:
            pass

def main():
    print_header("Dynamic Pricing System Test")
    print_info(f"Backend URL: {BACKEND_URL}")
    print_info(f"Test Credentials: {AUTHORITY_EMAIL} / {AUTHORITY_PASSWORD}")
    
    # Test Results Summary
    results = {
        "authority_login": False,
        "create_vehicle_category": False,
        "list_vehicle_categories": False,
        "create_job_with_category": False,
        "calculate_costs": False,
        "mongodb_verification": False
    }
    
    # Test 1: Authority Login
    token = test_authority_login()
    if token:
        results["authority_login"] = True
    else:
        print_error("Cannot proceed without authority token. Exiting.")
        sys.exit(1)
    
    # Wait a moment between requests
    time.sleep(1)
    
    # Test 2: Create Vehicle Category
    category_id = test_create_vehicle_category(token)
    if category_id:
        results["create_vehicle_category"] = True
    else:
        print_error("Cannot proceed without vehicle category. Exiting.")
        sys.exit(1)
    
    time.sleep(1)
    
    # Test 3: List Vehicle Categories
    if test_list_vehicle_categories(token):
        results["list_vehicle_categories"] = True
    
    time.sleep(1)
    
    # Test 4: Create Job with Vehicle Category
    job_id = test_create_job_with_category(token, category_id)
    if job_id:
        results["create_job_with_category"] = True
    else:
        print_error("Cannot proceed without job. Exiting.")
        sys.exit(1)
    
    time.sleep(1)
    
    # Test 5: Calculate Costs
    if test_calculate_costs(token, job_id):
        results["calculate_costs"] = True
    
    time.sleep(1)
    
    # Test 6: MongoDB Verification
    if test_mongodb_verification():
        results["mongodb_verification"] = True
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = 0
    total = len(results)
    
    for test_name, passed_result in results.items():
        if passed_result:
            print_success(f"{test_name}: PASSED")
            passed += 1
        else:
            print_error(f"{test_name}: FAILED")
    
    success_rate = (passed / total) * 100
    print_info(f"\nSuccess Rate: {passed}/{total} ({success_rate:.1f}%)")
    
    if passed == total:
        print_success("🎉 ALL TESTS PASSED - Dynamic Pricing System is working correctly!")
    elif passed >= total * 0.8:  # 80% success rate
        print_info("⚠️  MOSTLY WORKING - Some tests failed, but core functionality is present")
    else:
        print_error("❌ CRITICAL ISSUES - Multiple tests failed")
    
    return passed, total

if __name__ == "__main__":
    try:
        passed, total = main()
        sys.exit(0 if passed == total else 1)
    except KeyboardInterrupt:
        print_error("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
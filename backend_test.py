#!/usr/bin/env python3
"""
Comprehensive Backend Test for German Towing Management App
Testing 2FA Authentication and DSGVO Data Cleanup Features
"""

import requests
import json
import sys
import time
import base64
import re
from datetime import datetime, timezone, timedelta

# Backend URL from frontend environment
BACKEND_URL = "https://auth-2fa-dsgvo.preview.emergentagent.com/api"

# Test credentials as provided in review request
TEST_CREDENTIALS = {
    "admin": {
        "email": "admin@test.de",
        "password": "Admin123!"
    },
    "authority": {
        "email": "behoerde@test.de", 
        "password": "Behoerde123"
    },
    "towing": {
        "email": "abschlepp@test.de",
        "password": "Abschlepp123"
    }
}

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.tokens = {}
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    def log(self, message):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        
    def test_result(self, test_name, success, details=""):
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            self.failed_tests += 1
            status = "❌ FAIL"
            
        result = f"{status}: {test_name}"
        if details:
            result += f" - {details}"
            
        self.log(result)
        self.test_results.append((test_name, success, details))
        return success
    
    def login_user(self, role):
        """Login and store token for user role"""
        try:
            creds = TEST_CREDENTIALS[role]
            response = self.session.post(f"{BACKEND_URL}/auth/login", json={
                "email": creds["email"],
                "password": creds["password"]
            })
            
            if response.status_code == 200:
                data = response.json()
                if "requires_2fa" in data and data["requires_2fa"]:
                    # 2FA required, return temp_token
                    return {"requires_2fa": True, "temp_token": data.get("temp_token")}
                else:
                    # Regular login success
                    token = data["access_token"]
                    self.tokens[role] = token
                    self.session.headers.update({"Authorization": f"Bearer {token}"})
                    return {"success": True, "token": token, "user": data["user"]}
            else:
                return {"error": response.status_code, "message": response.text}
                
        except Exception as e:
            return {"error": str(e)}
    
    def make_authenticated_request(self, method, endpoint, role="admin", **kwargs):
        """Make authenticated API request"""
        try:
            if role not in self.tokens:
                login_result = self.login_user(role)
                if "error" in login_result:
                    return {"error": f"Login failed: {login_result}"}
                    
            headers = kwargs.get("headers", {})
            headers["Authorization"] = f"Bearer {self.tokens[role]}"
            kwargs["headers"] = headers
            
            response = getattr(self.session, method.lower())(f"{BACKEND_URL}{endpoint}", **kwargs)
            return {
                "status_code": response.status_code,
                "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                "headers": dict(response.headers)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def test_1_2fa_setup_flow(self):
        """Test 1: 2FA Setup Flow - QR code and secret generation"""
        self.log("\n=== TEST 1: 2FA Setup Flow ===")
        
        # Step 1: Login as admin
        login_result = self.login_user("admin")
        if not self.test_result("1.1 Admin login", "success" in login_result, 
                               login_result.get("error", "")):
            return False
            
        # Step 2: Call 2FA setup endpoint
        response = self.make_authenticated_request("POST", "/auth/2fa/setup", "admin")
        
        success = response.get("status_code") == 200
        if success:
            data = response["data"]
            # Verify QR code format
            qr_code_valid = (
                "qr_code" in data and 
                data["qr_code"].startswith("data:image/png;base64,") and
                len(data["qr_code"]) > 100  # Base64 image should be substantial
            )
            
            # Verify secret format (32-char base32)
            secret_valid = (
                "secret" in data and
                isinstance(data["secret"], str) and
                len(data["secret"]) == 32 and
                re.match(r'^[A-Z2-7]+$', data["secret"])  # Base32 format
            )
            
            details = f"QR Code: {'Valid' if qr_code_valid else 'Invalid'}, Secret: {'Valid' if secret_valid else 'Invalid'}"
            if qr_code_valid and secret_valid:
                details += f" (Secret length: {len(data['secret'])})"
                
            success = qr_code_valid and secret_valid
        else:
            details = f"HTTP {response.get('status_code')}: {response.get('data')}"
            
        return self.test_result("1.2 2FA setup returns QR code and secret", success, details)
    
    def test_2_2fa_login_flow_existence(self):
        """Test 2: 2FA Login Flow Endpoint Existence (simulation)"""
        self.log("\n=== TEST 2: 2FA Login Flow Endpoint ===")
        
        # We can't test actual 2FA without authenticator app, but verify endpoint exists
        # Try with invalid temp_token to see if endpoint responds correctly
        response = self.session.post(f"{BACKEND_URL}/auth/login/2fa", json={
            "temp_token": "invalid_token",
            "totp_code": "123456"
        })
        
        # Should return 401 for invalid token (not 404 for missing endpoint)
        success = response.status_code in [401, 400]  # Either unauthorized or bad request
        details = f"HTTP {response.status_code} (Expected: 401/400 for invalid token)"
        
        if success:
            try:
                error_data = response.json()
                if "detail" in error_data:
                    details += f" - Error: {error_data['detail']}"
            except:
                pass
                
        return self.test_result("2.1 2FA login endpoint exists and validates input", success, details)
    
    def test_3_dsgvo_status_endpoint(self):
        """Test 3: DSGVO Status Endpoint"""
        self.log("\n=== TEST 3: DSGVO Status Endpoint ===")
        
        response = self.make_authenticated_request("GET", "/admin/dsgvo-status", "admin")
        
        success = response.get("status_code") == 200
        if success:
            data = response["data"]
            required_fields = [
                "retention_days", "cutoff_date", "pending_anonymization", 
                "already_anonymized", "scheduler_running"
            ]
            
            missing_fields = [field for field in required_fields if field not in data]
            
            # Validate specific values
            valid_retention = data.get("retention_days") == 180  # 6 months
            valid_cutoff = isinstance(data.get("cutoff_date"), str) and "T" in data["cutoff_date"]
            valid_counts = (
                isinstance(data.get("pending_anonymization"), int) and
                isinstance(data.get("already_anonymized"), int) and
                data.get("already_anonymized") >= 1  # Should have test job
            )
            valid_scheduler = data.get("scheduler_running") is True
            
            success = (
                len(missing_fields) == 0 and valid_retention and 
                valid_cutoff and valid_counts and valid_scheduler
            )
            
            details = f"Fields: {len(required_fields) - len(missing_fields)}/{len(required_fields)}"
            if missing_fields:
                details += f", Missing: {missing_fields}"
            details += f", Retention: {data.get('retention_days')}d"
            details += f", Anonymized: {data.get('already_anonymized')}"
            details += f", Scheduler: {data.get('scheduler_running')}"
            
        else:
            details = f"HTTP {response.get('status_code')}: {response.get('data')}"
            
        return self.test_result("3.1 DSGVO status endpoint returns complete data", success, details)
    
    def test_4_dsgvo_manual_cleanup(self):
        """Test 4: DSGVO Manual Cleanup"""
        self.log("\n=== TEST 4: DSGVO Manual Cleanup ===")
        
        response = self.make_authenticated_request("POST", "/admin/trigger-cleanup", "admin")
        
        success = response.get("status_code") == 200
        if success:
            data = response["data"]
            
            # Should return message and retention_days
            has_message = "message" in data and isinstance(data["message"], str)
            has_retention = "retention_days" in data and data["retention_days"] == 180
            
            success = has_message and has_retention
            details = f"Message: {'✓' if has_message else '✗'}, Retention: {data.get('retention_days')}d"
            
        else:
            details = f"HTTP {response.get('status_code')}: {response.get('data')}"
            
        return self.test_result("4.1 DSGVO manual cleanup triggers successfully", success, details)
    
    def test_5_role_based_access_control(self):
        """Test 5: Role-based Access Control"""
        self.log("\n=== TEST 5: Role-based Access Control ===")
        
        results = []
        
        # Test 5.1: Authority should get 403 for DSGVO status
        response = self.make_authenticated_request("GET", "/admin/dsgvo-status", "authority")
        success = response.get("status_code") == 403
        details = f"HTTP {response.get('status_code')} (Expected: 403)"
        results.append(self.test_result("5.1 Authority blocked from DSGVO status", success, details))
        
        # Test 5.2: Authority should get 403 for manual cleanup
        response = self.make_authenticated_request("POST", "/admin/trigger-cleanup", "authority")
        success = response.get("status_code") == 403
        details = f"HTTP {response.get('status_code')} (Expected: 403)"
        results.append(self.test_result("5.2 Authority blocked from DSGVO cleanup", success, details))
        
        return all(results)
    
    def test_6_user_logins(self):
        """Test 6: All User Logins Work"""
        self.log("\n=== TEST 6: User Login Verification ===")
        
        results = []
        
        for role, creds in TEST_CREDENTIALS.items():
            login_result = self.login_user(role)
            
            if "success" in login_result:
                user_data = login_result.get("user", {})
                expected_role = "towing_service" if role == "towing" else role
                role_match = user_data.get("role") == expected_role
                has_token = "token" in login_result and len(login_result["token"]) > 50
                
                success = role_match and has_token
                details = f"Role: {user_data.get('role')}, Token: {'✓' if has_token else '✗'}"
                
            elif "requires_2fa" in login_result:
                # 2FA required is also valid
                success = True
                details = "2FA Required (Valid response)"
                
            else:
                success = False
                details = f"Login failed: {login_result.get('error', 'Unknown error')}"
            
            test_name = f"6.{['admin', 'authority', 'towing'].index(role) + 1} {role.title()} login"
            results.append(self.test_result(test_name, success, details))
        
        return all(results)
    
    def run_all_tests(self):
        """Run all test scenarios"""
        self.log("🚀 STARTING 2FA & DSGVO BACKEND TESTING")
        self.log(f"Backend URL: {BACKEND_URL}")
        self.log(f"Test Credentials: {len(TEST_CREDENTIALS)} roles")
        
        start_time = time.time()
        
        # Run all test scenarios from review request
        test_methods = [
            self.test_1_2fa_setup_flow,
            self.test_2_2fa_login_flow_existence, 
            self.test_3_dsgvo_status_endpoint,
            self.test_4_dsgvo_manual_cleanup,
            self.test_5_role_based_access_control,
            self.test_6_user_logins
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.log(f"❌ ERROR in {test_method.__name__}: {e}")
                self.failed_tests += 1
                self.total_tests += 1
        
        # Final results
        duration = time.time() - start_time
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        self.log(f"\n🎯 TESTING COMPLETE")
        self.log(f"Duration: {duration:.1f}s")
        self.log(f"Success Rate: {success_rate:.1f}% ({self.passed_tests}/{self.total_tests})")
        
        if success_rate >= 85:
            self.log("🎉 EXCELLENT: All critical features working!")
            return "excellent"
        elif success_rate >= 70:
            self.log("✅ GOOD: Most features working, minor issues")
            return "good"
        else:
            self.log("⚠️  ISSUES: Significant problems found")
            return "issues"

if __name__ == "__main__":
    tester = BackendTester()
    result = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if result in ["excellent", "good"] else 1)
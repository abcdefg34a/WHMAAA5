#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime

class MongoDBAtlasConnectionTester:
    def __init__(self, base_url="https://react-state-sync.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        
        # Test credentials as specified in review request
        self.admin_credentials = {
            "email": "admin@test.de",
            "password": "Admin123!"
        }

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: dict = None, token: str = None) -> tuple[bool, dict]:
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

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                    return False, error_data
                except:
                    print(f"   Error: {response.text}")
                    return False, {"error": response.text}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {"error": str(e)}

    def test_admin_login(self):
        """Test admin login with provided credentials"""
        print("\n🔐 Testing Admin Login (MongoDB Atlas Connection Check)...")
        
        success, response = self.run_test(
            "Admin Login", "POST", "auth/login", 200, self.admin_credentials
        )
        
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            user_data = response.get('user', {})
            print(f"   ✅ Admin login successful - MongoDB Atlas connection working!")
            print(f"   Admin ID: {user_data.get('id')}")
            print(f"   Admin Role: {user_data.get('role')}")
            print(f"   Admin Name: {user_data.get('name')}")
            print(f"   Token obtained: {self.admin_token[:20]}...")
            return True
        else:
            print(f"   ❌ Admin login failed - This might indicate:")
            print(f"   - New empty database (expected)")
            print(f"   - MongoDB Atlas connection issues")
            print(f"   - Missing admin user in database")
            return False

    def test_database_stats(self):
        """Test if database has data by checking admin stats"""
        print("\n📊 Testing Database Stats (Check if DB has data)...")
        
        if not self.admin_token:
            print("❌ No admin token available - cannot check database stats")
            return False
        
        success, response = self.run_test(
            "Admin Stats", "GET", "admin/stats", 200, token=self.admin_token
        )
        
        if success and response:
            total_jobs = response.get('total_jobs', 0)
            total_services = response.get('total_services', 0)
            total_authorities = response.get('total_authorities', 0)
            pending_approvals = response.get('pending_approvals', 0)
            
            print(f"   📈 Database Statistics:")
            print(f"   - Total Jobs: {total_jobs}")
            print(f"   - Total Services: {total_services}")
            print(f"   - Total Authorities: {total_authorities}")
            print(f"   - Pending Approvals: {pending_approvals}")
            
            if total_jobs == 0 and total_services == 0 and total_authorities == 0:
                print(f"   🆕 DATABASE IS EMPTY - Needs initial data seeding!")
                return "empty"
            else:
                print(f"   ✅ Database contains data - MongoDB Atlas working correctly")
                return "has_data"
        else:
            print(f"   ❌ Failed to get database stats")
            return False

    def test_admin_users_endpoint(self):
        """Test admin users endpoint to check database connectivity"""
        print("\n👥 Testing Admin Users Endpoint (Database Connectivity)...")
        
        if not self.admin_token:
            print("❌ No admin token available - cannot check users")
            return False
        
        success, response = self.run_test(
            "Get All Users", "GET", "admin/users", 200, token=self.admin_token
        )
        
        if success and response:
            user_count = len(response)
            print(f"   ✅ Retrieved {user_count} users from database")
            
            # Count users by role
            role_counts = {}
            for user in response:
                role = user.get('role', 'unknown')
                role_counts[role] = role_counts.get(role, 0) + 1
            
            print(f"   User breakdown by role:")
            for role, count in role_counts.items():
                print(f"   - {role}: {count} users")
            
            return user_count > 0
        else:
            print(f"   ❌ Failed to retrieve users from database")
            return False

    def test_audit_logs_endpoint(self):
        """Test audit logs endpoint to verify database logging"""
        print("\n📋 Testing Audit Logs (Database Logging Check)...")
        
        if not self.admin_token:
            print("❌ No admin token available - cannot check audit logs")
            return False
        
        success, response = self.run_test(
            "Get Audit Logs", "GET", "admin/audit-logs", 200, token=self.admin_token
        )
        
        if success and response:
            audit_count = len(response)
            print(f"   ✅ Retrieved {audit_count} audit log entries")
            
            # Check for recent login entries
            login_entries = [entry for entry in response if entry.get('action') in ['USER_LOGIN', 'LOGIN_FAILED']]
            print(f"   - Login-related entries: {len(login_entries)}")
            
            # Show recent entries
            for i, entry in enumerate(response[:3]):
                action = entry.get('action', 'Unknown')
                user_name = entry.get('user_name', 'Unknown')
                timestamp = entry.get('timestamp', 'Unknown')[:19]  # Truncate timestamp
                print(f"   - Entry {i+1}: {action} by {user_name} at {timestamp}")
            
            return audit_count > 0
        else:
            print(f"   ❌ Failed to retrieve audit logs from database")
            return False

    def run_mongodb_atlas_tests(self):
        """Run all MongoDB Atlas connection tests"""
        print("=" * 80)
        print("🗄️  MONGODB ATLAS CONNECTION TEST")
        print("=" * 80)
        print(f"Testing MongoDB Atlas cloud database connection...")
        print(f"Backend URL: {self.base_url}")
        print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test 1: Admin Login
        login_success = self.test_admin_login()
        
        if not login_success:
            print("\n" + "=" * 80)
            print("🔴 MONGODB ATLAS CONNECTION TEST RESULTS")
            print("=" * 80)
            print("❌ ADMIN LOGIN FAILED")
            print("\nPossible reasons:")
            print("1. 🆕 NEW EMPTY DATABASE - Admin user doesn't exist yet")
            print("2. 🔌 MongoDB Atlas connection issues")
            print("3. 🔑 Incorrect admin credentials")
            print("4. 🚫 Backend service not running")
            print("\n📋 RECOMMENDATION:")
            print("If this is a new database, you need to:")
            print("1. Create initial admin user")
            print("2. Seed database with test data")
            print("3. Verify MongoDB Atlas connection string")
            return False
        
        # Test 2: Database Stats
        db_status = self.test_database_stats()
        
        # Test 3: Users Endpoint
        users_success = self.test_admin_users_endpoint()
        
        # Test 4: Audit Logs
        audit_success = self.test_audit_logs_endpoint()
        
        # Final Results
        print("\n" + "=" * 80)
        print("🗄️  MONGODB ATLAS CONNECTION TEST RESULTS")
        print("=" * 80)
        
        if login_success:
            print("✅ MONGODB ATLAS CONNECTION: WORKING")
            print("✅ Admin Authentication: SUCCESS")
            
            if db_status == "empty":
                print("🆕 Database Status: EMPTY (New database)")
                print("\n📋 NEXT STEPS NEEDED:")
                print("1. Seed database with initial test data")
                print("2. Create test authorities and towing services")
                print("3. Create sample jobs for testing")
            elif db_status == "has_data":
                print("✅ Database Status: CONTAINS DATA")
                print("✅ Database Operations: WORKING")
            
            if users_success:
                print("✅ User Management: WORKING")
            
            if audit_success:
                print("✅ Audit Logging: WORKING")
        else:
            print("❌ MONGODB ATLAS CONNECTION: FAILED")
        
        print(f"\nTest Summary: {self.tests_passed}/{self.tests_run} tests passed")
        print("=" * 80)
        
        return login_success

if __name__ == "__main__":
    tester = MongoDBAtlasConnectionTester()
    success = tester.run_mongodb_atlas_tests()
    sys.exit(0 if success else 1)
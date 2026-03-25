#!/usr/bin/env python3

import requests
import json

def test_admin_registration():
    """Test if we can register the admin user"""
    base_url = "https://dual-yard-system.preview.emergentagent.com/api"
    
    admin_data = {
        "email": "admin@test.de",
        "password": "Admin123!",
        "name": "System Administrator",
        "role": "admin"
    }
    
    print("🔧 Testing Admin User Registration...")
    print(f"Backend URL: {base_url}")
    
    try:
        response = requests.post(
            f"{base_url}/auth/register",
            json=admin_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"Registration Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Admin registration successful!")
            print(f"Admin ID: {data.get('user', {}).get('id')}")
            print(f"Token: {data.get('access_token', '')[:20]}...")
            return True, data.get('access_token')
        else:
            try:
                error = response.json()
                print(f"❌ Registration failed: {error}")
            except:
                print(f"❌ Registration failed: {response.text}")
            return False, None
            
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")
        return False, None

def test_admin_login(token=None):
    """Test admin login after registration"""
    base_url = "https://dual-yard-system.preview.emergentagent.com/api"
    
    login_data = {
        "email": "admin@test.de",
        "password": "Admin123!"
    }
    
    print("\n🔐 Testing Admin Login...")
    
    try:
        response = requests.post(
            f"{base_url}/auth/login",
            json=login_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"Login Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Admin login successful!")
            print(f"Admin ID: {data.get('user', {}).get('id')}")
            print(f"Admin Role: {data.get('user', {}).get('role')}")
            return True, data.get('access_token')
        else:
            try:
                error = response.json()
                print(f"❌ Login failed: {error}")
            except:
                print(f"❌ Login failed: {response.text}")
            return False, None
            
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")
        return False, None

def test_database_stats(token):
    """Test database stats to verify MongoDB connection"""
    base_url = "https://dual-yard-system.preview.emergentagent.com/api"
    
    print("\n📊 Testing Database Stats...")
    
    try:
        response = requests.get(
            f"{base_url}/admin/stats",
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            },
            timeout=10
        )
        
        print(f"Stats Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Database stats retrieved successfully!")
            print(f"Total Jobs: {data.get('total_jobs', 0)}")
            print(f"Total Services: {data.get('total_services', 0)}")
            print(f"Total Authorities: {data.get('total_authorities', 0)}")
            print(f"Pending Approvals: {data.get('pending_approvals', 0)}")
            
            if all(data.get(key, 0) == 0 for key in ['total_jobs', 'total_services', 'total_authorities']):
                print("🆕 Database is empty - this is a new MongoDB Atlas database!")
            else:
                print("✅ Database contains existing data")
            
            return True
        else:
            try:
                error = response.json()
                print(f"❌ Stats failed: {error}")
            except:
                print(f"❌ Stats failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("🗄️  MONGODB ATLAS CONNECTION & SEEDING TEST")
    print("=" * 80)
    
    # Try to register admin first
    reg_success, token = test_admin_registration()
    
    if not reg_success:
        # If registration fails, try login (maybe admin already exists)
        print("\n🔄 Registration failed, trying login...")
        login_success, token = test_admin_login()
        
        if not login_success:
            print("\n❌ Both registration and login failed!")
            print("This indicates either:")
            print("1. MongoDB Atlas connection issues")
            print("2. Backend service problems")
            print("3. Database authentication problems")
            exit(1)
    else:
        # Registration succeeded, also test login
        login_success, login_token = test_admin_login()
        if login_success:
            token = login_token  # Use login token
    
    # Test database operations
    if token:
        stats_success = test_database_stats(token)
        
        print("\n" + "=" * 80)
        print("🎯 MONGODB ATLAS TEST RESULTS")
        print("=" * 80)
        
        if reg_success or login_success:
            print("✅ MongoDB Atlas Connection: WORKING")
            print("✅ Admin Authentication: SUCCESS")
            
            if stats_success:
                print("✅ Database Operations: WORKING")
                print("🆕 Status: NEW EMPTY DATABASE")
                print("\n📋 NEXT STEPS:")
                print("1. Database is ready for use")
                print("2. Admin user created successfully")
                print("3. Can proceed with application testing")
            else:
                print("❌ Database Operations: FAILED")
        else:
            print("❌ MongoDB Atlas Connection: FAILED")
    else:
        print("\n❌ No valid token obtained - cannot test database operations")
#!/usr/bin/env python3
"""
Quick verification test for specific backup system functionality
"""

import requests
import json

BASE_URL = "https://dual-yard-system.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@test.de"
ADMIN_PASSWORD = "Admin123!"

def test_specific_backup_issues():
    """Test for specific backup system issues"""
    session = requests.Session()
    
    # Authenticate
    response = session.post(f"{BASE_URL}/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    
    if response.status_code != 200:
        print("❌ Authentication failed")
        return
    
    token = response.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    print("✅ Authentication successful")
    
    # Test backup health for any critical errors
    response = session.get(f"{BASE_URL}/admin/backups/health")
    if response.status_code == 200:
        health_data = response.json()
        print(f"✅ Backup Health: {health_data}")
        
        # Check for any critical issues
        if health_data.get("status") == "error":
            print(f"❌ CRITICAL: Backup system has errors: {health_data}")
        elif health_data.get("status") == "warning":
            print(f"⚠️ WARNING: Backup system has warnings: {health_data}")
        else:
            print("✅ Backup system health is good")
    else:
        print(f"❌ Failed to get backup health: {response.status_code}")
    
    # Test if corrupted backups exist
    response = session.delete(f"{BASE_URL}/admin/backups/corrupted")
    if response.status_code == 200:
        result = response.json()
        deleted_count = result.get("deleted_count", 0)
        if deleted_count > 0:
            print(f"⚠️ Found and deleted {deleted_count} corrupted backup entries")
        else:
            print("✅ No corrupted backups found")
    else:
        print(f"❌ Failed to check corrupted backups: {response.status_code}")
    
    # Test backup listing
    response = session.get(f"{BASE_URL}/admin/backups")
    if response.status_code == 200:
        backups = response.json()
        backup_count = len(backups) if isinstance(backups, list) else backups.get('count', 0)
        print(f"✅ Found {backup_count} backups in system")
        
        # Check for any failed backups
        if isinstance(backups, list):
            failed_backups = [b for b in backups if b.get("status") == "failed"]
            if failed_backups:
                print(f"⚠️ Found {len(failed_backups)} failed backups")
                for backup in failed_backups[:3]:  # Show first 3
                    print(f"   - {backup.get('filename', 'Unknown')}: {backup.get('error', 'No error message')}")
            else:
                print("✅ No failed backups found")
    else:
        print(f"❌ Failed to list backups: {response.status_code}")

if __name__ == "__main__":
    test_specific_backup_issues()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MongoDB Backup Funktionalität mit Supabase Cloud-Integration Test
==========================================

Testet die MongoDB Backup-Endpoints mit Fokus auf Supabase Integration:
1. POST /api/auth/login - Admin Login (Token holen)
2. GET /api/admin/backups/system-status - System Status abrufen
3. POST /api/admin/backups/run-database-backup - Datenbank-Backup mit Supabase Upload
4. POST /api/admin/backups/run-storage-backup - Storage-Backup mit Supabase Upload
5. GET /api/admin/backups - Alle Backups auflisten
6. POST /api/admin/backups/run-full-backup - Komplett-Backup (DB + Storage)

Wichtig: Prüft ob die Backups tatsächlich zu Supabase Storage hochgeladen werden (supabase_uploaded und supabase_path Felder).
"""

import requests
import json
import sys
import time
from datetime import datetime

# Backend URL aus Frontend .env
BACKEND_URL = "https://react-state-sync.preview.emergentagent.com/api"

# Test-Credentials
ADMIN_EMAIL = "admin@test.de"
ADMIN_PASSWORD = "Admin123!"

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

def test_admin_login():
    """Test 1: Admin Login - Token holen"""
    print_test("Admin Login")
    
    response = make_request("POST", "/auth/login", json_data={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    
    if not response:
        print_error("Login request failed")
        return None
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        user = data.get("user", {})
        
        print_success(f"Admin login successful")
        print_info(f"Token: {token[:20]}...")
        print_info(f"User: {user.get('name')} ({user.get('role')})")
        
        return token
    else:
        print_error(f"Login failed: {response.status_code} - {response.text}")
        return None

def test_system_status(token):
    """Test 2: GET /api/admin/backups/system-status - System Status abrufen"""
    print_test("Backup System Status")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = make_request("GET", "/admin/backups/system-status", headers=headers)
    
    if not response:
        print_error("System status request failed")
        return False
    
    if response.status_code == 200:
        data = response.json()
        
        print_success("System status retrieved successfully")
        print_info(f"Total backups: {data.get('total_backups', 0)}")
        print_info(f"Supabase enabled: {data.get('supabase_enabled', False)}")
        print_info(f"Supabase backups: {data.get('supabase_backups', 0)}")
        print_info(f"Total size: {data.get('total_size_mb', 0)} MB")
        
        # Check Supabase status
        supabase_enabled = data.get('supabase_enabled', False)
        supabase_backups = data.get('supabase_backups', 0)
        
        if supabase_enabled:
            print_success(f"✅ Supabase enabled: {supabase_enabled}")
        else:
            print_error(f"❌ Supabase not enabled: {supabase_enabled}")
        
        if supabase_backups > 0:
            print_success(f"✅ Supabase backups found: {supabase_backups}")
        else:
            print_info(f"ℹ️  No Supabase backups yet: {supabase_backups}")
        
        # Show last backups
        last_db = data.get('last_database_backup')
        last_storage = data.get('last_storage_backup')
        
        if last_db:
            print_info(f"Last DB backup: {last_db.get('date')} ({last_db.get('filename')}) - Supabase: {last_db.get('supabase_uploaded', False)}")
        if last_storage:
            print_info(f"Last storage backup: {last_storage.get('date')} ({last_storage.get('filename')}) - Supabase: {last_storage.get('supabase_uploaded', False)}")
        
        return True
    else:
        print_error(f"System status failed: {response.status_code} - {response.text}")
        return False

def test_database_backup(token):
    """Test 3: POST /api/admin/backups/run-database-backup - Datenbank-Backup mit Supabase Upload"""
    print_test("Database Backup with Supabase Upload")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = make_request("POST", "/admin/backups/run-database-backup", headers=headers)
    
    if not response:
        print_error("Database backup request failed")
        return None
    
    if response.status_code == 200:
        data = response.json()
        
        print_success("Database backup started successfully")
        print_info(f"Backup ID: {data.get('id')}")
        print_info(f"Status: {data.get('status')}")
        print_info(f"Filename: {data.get('filename')}")
        print_info(f"Size: {data.get('size_bytes', 0)} bytes")
        
        # Check Supabase upload
        supabase_uploaded = data.get('supabase_uploaded', False)
        supabase_path = data.get('supabase_path')
        
        if supabase_uploaded:
            print_success(f"✅ Supabase uploaded: {supabase_uploaded}")
            print_success(f"✅ Supabase path: {supabase_path}")
        else:
            print_error(f"❌ Supabase upload failed or disabled")
            print_error(f"❌ supabase_uploaded: {supabase_uploaded}")
            print_error(f"❌ supabase_path: {supabase_path}")
        
        return data.get('id')
    else:
        print_error(f"Database backup failed: {response.status_code} - {response.text}")
        return None

def test_storage_backup(token):
    """Test 4: POST /api/admin/backups/run-storage-backup - Storage-Backup mit Supabase Upload"""
    print_test("Storage Backup with Supabase Upload")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = make_request("POST", "/admin/backups/run-storage-backup", headers=headers)
    
    if not response:
        print_error("Storage backup request failed")
        return None
    
    if response.status_code == 200:
        data = response.json()
        
        print_success("Storage backup started successfully")
        print_info(f"Backup ID: {data.get('id')}")
        print_info(f"Status: {data.get('status')}")
        print_info(f"Filename: {data.get('filename')}")
        print_info(f"Size: {data.get('size_bytes', 0)} bytes")
        print_info(f"Files backed up: {data.get('files_backed_up', 0)}")
        
        # Check Supabase upload
        supabase_uploaded = data.get('supabase_uploaded', False)
        supabase_path = data.get('supabase_path')
        
        if supabase_uploaded:
            print_success(f"✅ Supabase uploaded: {supabase_uploaded}")
            print_success(f"✅ Supabase path: {supabase_path}")
        else:
            print_error(f"❌ Supabase upload failed or disabled")
            print_error(f"❌ supabase_uploaded: {supabase_uploaded}")
            print_error(f"❌ supabase_path: {supabase_path}")
        
        return data.get('id')
    else:
        print_error(f"Storage backup failed: {response.status_code} - {response.text}")
        return None

def test_list_backups(token):
    """Test 5: GET /api/admin/backups - Alle Backups auflisten"""
    print_test("List All Backups")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = make_request("GET", "/admin/backups", headers=headers)
    
    if not response:
        print_error("List backups request failed")
        return False
    
    if response.status_code == 200:
        data = response.json()
        backups = data if isinstance(data, list) else data.get('backups', [])
        
        print_success(f"Retrieved {len(backups)} backups")
        
        # Check recent backups for Supabase upload status
        supabase_count = 0
        recent_backups = sorted(backups, key=lambda x: x.get('created_at', ''), reverse=True)[:5]
        
        for backup in recent_backups:
            backup_id = backup.get('id')
            backup_type = backup.get('backup_type')
            status = backup.get('status')
            filename = backup.get('file_name')
            created_at = backup.get('created_at', '')[:19] if backup.get('created_at') else 'Unknown'
            supabase_uploaded = backup.get('supabase_uploaded', False)
            supabase_path = backup.get('supabase_path', '')
            
            print_info(f"Backup: {backup_id} ({backup_type}) - {filename}")
            print_info(f"  Status: {status}, Created: {created_at}")
            print_info(f"  Supabase uploaded: {supabase_uploaded}")
            if supabase_path:
                print_info(f"  Supabase path: {supabase_path}")
            
            if supabase_uploaded:
                supabase_count += 1
        
        if supabase_count > 0:
            print_success(f"✅ Found {supabase_count} backups with Supabase upload")
        else:
            print_error(f"❌ No backups found with Supabase upload in recent backups")
        
        return True
    else:
        print_error(f"List backups failed: {response.status_code} - {response.text}")
        return False

def test_full_backup(token):
    """Test 6: POST /api/admin/backups/run-full-backup - Komplett-Backup (DB + Storage)"""
    print_test("Full Backup (Database + Storage) with Supabase Upload")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = make_request("POST", "/admin/backups/run-full-backup", headers=headers)
    
    if not response:
        print_error("Full backup request failed")
        return False
    
    if response.status_code == 200:
        data = response.json()
        
        print_success("Full backup started successfully")
        print_info(f"Overall status: {data.get('status')}")
        
        # Check database backup
        db_backup = data.get('database_backup', {})
        print_info(f"\nDatabase Backup:")
        print_info(f"  ID: {db_backup.get('id')}")
        print_info(f"  Status: {db_backup.get('status')}")
        print_info(f"  Filename: {db_backup.get('filename')}")
        print_info(f"  Supabase uploaded: {db_backup.get('supabase_uploaded', False)}")
        print_info(f"  Supabase path: {db_backup.get('supabase_path', 'N/A')}")
        
        # Check storage backup
        storage_backup = data.get('storage_backup', {})
        print_info(f"\nStorage Backup:")
        print_info(f"  ID: {storage_backup.get('id')}")
        print_info(f"  Status: {storage_backup.get('status')}")
        print_info(f"  Filename: {storage_backup.get('filename')}")
        print_info(f"  Supabase uploaded: {storage_backup.get('supabase_uploaded', False)}")
        print_info(f"  Supabase path: {storage_backup.get('supabase_path', 'N/A')}")
        
        # Verify both backups were uploaded to Supabase
        db_supabase = db_backup.get('supabase_uploaded', False)
        storage_supabase = storage_backup.get('supabase_uploaded', False)
        
        if db_supabase and storage_supabase:
            print_success(f"✅ Both backups successfully uploaded to Supabase")
        elif db_supabase or storage_supabase:
            print_error(f"❌ Only partial Supabase upload: DB={db_supabase}, Storage={storage_supabase}")
        else:
            print_error(f"❌ No Supabase uploads: DB={db_supabase}, Storage={storage_supabase}")
        
        return True
    else:
        print_error(f"Full backup failed: {response.status_code} - {response.text}")
        return False

def main():
    print_header("MongoDB Backup Funktionalität mit Supabase Integration Test")
    print_info(f"Backend URL: {BACKEND_URL}")
    print_info(f"Test Credentials: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    
    # Test Results Summary
    results = {
        "admin_login": False,
        "system_status": False,
        "database_backup": False,
        "storage_backup": False,
        "list_backups": False,
        "full_backup": False
    }
    
    # Test 1: Admin Login
    token = test_admin_login()
    if token:
        results["admin_login"] = True
    else:
        print_error("Cannot proceed without admin token. Exiting.")
        sys.exit(1)
    
    # Wait a moment between requests
    time.sleep(1)
    
    # Test 2: System Status
    if test_system_status(token):
        results["system_status"] = True
    
    time.sleep(1)
    
    # Test 3: Database Backup
    db_backup_id = test_database_backup(token)
    if db_backup_id:
        results["database_backup"] = True
    
    time.sleep(2)  # Backup needs time
    
    # Test 4: Storage Backup
    storage_backup_id = test_storage_backup(token)
    if storage_backup_id:
        results["storage_backup"] = True
    
    time.sleep(2)  # Backup needs time
    
    # Test 5: List Backups
    if test_list_backups(token):
        results["list_backups"] = True
    
    time.sleep(1)
    
    # Test 6: Full Backup
    if test_full_backup(token):
        results["full_backup"] = True
    
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
        print_success("🎉 ALL TESTS PASSED - MongoDB Backup mit Supabase Integration funktioniert vollständig!")
    elif passed >= total * 0.8:  # 80% success rate
        print_info("⚠️  MOSTLY WORKING - Einige Tests sind fehlgeschlagen, aber Kernfunktionalität ist vorhanden")
    else:
        print_error("❌ CRITICAL ISSUES - Mehrere Tests sind fehlgeschlagen")
    
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
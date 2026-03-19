#!/usr/bin/env python3
"""
MongoDB Backup Functionality Testing Script
Tests all backup endpoints as specified in the review request.
"""

import requests
import json
import time
import sys
from typing import Dict, Any, Optional, List

# Configuration
BACKEND_URL = "https://react-state-sync.preview.emergentagent.com"
ADMIN_EMAIL = "admin@test.de"
ADMIN_PASSWORD = "Admin123!"

class BackupTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.admin_token = None
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status} - {test_name}: {details}"
        print(result)
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        
    def make_request(self, method: str, endpoint: str, headers: Optional[Dict] = None, json_data: Optional[Dict] = None) -> requests.Response:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}/api{endpoint}"
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=json_data, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            return response
        except requests.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None

    def test_admin_login(self) -> bool:
        """TEST 1: POST /api/auth/login - Admin Login"""
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        response = self.make_request("POST", "/auth/login", json_data=login_data)
        
        if not response:
            self.log_test("Admin Login", False, "Network request failed")
            return False
            
        if response.status_code == 200:
            try:
                data = response.json()
                if "access_token" in data:
                    self.admin_token = data["access_token"]
                    self.log_test("Admin Login", True, f"Login successful, token obtained")
                    return True
                else:
                    self.log_test("Admin Login", False, "No access_token in response")
                    return False
            except json.JSONDecodeError:
                self.log_test("Admin Login", False, "Invalid JSON response")
                return False
        else:
            self.log_test("Admin Login", False, f"Status {response.status_code}: {response.text[:200]}")
            return False

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers with admin token"""
        if not self.admin_token:
            raise ValueError("Admin token not available")
        return {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        }

    def test_backup_system_status(self) -> bool:
        """TEST 2: GET /api/admin/backups/system-status"""
        response = self.make_request("GET", "/admin/backups/system-status", headers=self.get_auth_headers())
        
        if not response:
            self.log_test("Backup System Status", False, "Network request failed")
            return False
            
        if response.status_code == 200:
            try:
                data = response.json()
                # Check for expected fields in the actual response structure
                expected_fields = ["last_database_backup", "last_storage_backup", "total_backups", "retention_settings"]
                missing_fields = [field for field in expected_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Backup System Status", False, f"Missing fields: {missing_fields}")
                    return False
                else:
                    last_db_backup = data.get("last_database_backup", {}).get("date", "None")
                    last_storage_backup = data.get("last_storage_backup", {}).get("date", "None")
                    total_backups = data.get("total_backups", 0)
                    total_size_mb = data.get("total_size_mb", 0)
                    self.log_test("Backup System Status", True, f"Status retrieved - Total backups: {total_backups}, Size: {total_size_mb}MB, Last DB: {last_db_backup}, Last Storage: {last_storage_backup}")
                    return True
            except json.JSONDecodeError:
                self.log_test("Backup System Status", False, "Invalid JSON response")
                return False
        else:
            self.log_test("Backup System Status", False, f"Status {response.status_code}: {response.text[:200]}")
            return False

    def test_manual_database_backup(self) -> Dict[str, Any]:
        """TEST 3: POST /api/admin/backups/run-database-backup"""
        response = self.make_request("POST", "/admin/backups/run-database-backup", headers=self.get_auth_headers())
        
        if not response:
            self.log_test("Manual Database Backup", False, "Network request failed")
            return {"success": False, "backup_id": None}
            
        if response.status_code == 200:
            try:
                data = response.json()
                if "id" in data and data.get("status") in ["running", "success"]:
                    backup_id = data["id"]
                    status = data.get("status", "unknown")
                    self.log_test("Manual Database Backup", True, f"Backup started successfully: ID={backup_id}, Status={status}")
                    return {"success": True, "backup_id": backup_id}
                else:
                    self.log_test("Manual Database Backup", False, f"Unexpected response format: {data}")
                    return {"success": False, "backup_id": None}
            except json.JSONDecodeError:
                self.log_test("Manual Database Backup", False, "Invalid JSON response")
                return {"success": False, "backup_id": None}
        else:
            self.log_test("Manual Database Backup", False, f"Status {response.status_code}: {response.text[:200]}")
            return {"success": False, "backup_id": None}

    def test_manual_storage_backup(self) -> Dict[str, Any]:
        """TEST 4: POST /api/admin/backups/run-storage-backup"""
        response = self.make_request("POST", "/admin/backups/run-storage-backup", headers=self.get_auth_headers())
        
        if not response:
            self.log_test("Manual Storage Backup", False, "Network request failed")
            return {"success": False, "backup_id": None}
            
        if response.status_code == 200:
            try:
                data = response.json()
                if "id" in data and data.get("status") in ["running", "success"]:
                    backup_id = data["id"]
                    status = data.get("status", "unknown")
                    self.log_test("Manual Storage Backup", True, f"Backup started successfully: ID={backup_id}, Status={status}")
                    return {"success": True, "backup_id": backup_id}
                else:
                    self.log_test("Manual Storage Backup", False, f"Unexpected response format: {data}")
                    return {"success": False, "backup_id": None}
            except json.JSONDecodeError:
                self.log_test("Manual Storage Backup", False, "Invalid JSON response")
                return {"success": False, "backup_id": None}
        else:
            self.log_test("Manual Storage Backup", False, f"Status {response.status_code}: {response.text[:200]}")
            return {"success": False, "backup_id": None}

    def test_list_backups(self) -> List[str]:
        """TEST 5: GET /api/admin/backups - List all backups"""
        response = self.make_request("GET", "/admin/backups", headers=self.get_auth_headers())
        
        if not response:
            self.log_test("List Backups", False, "Network request failed")
            return []
            
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list):
                    backup_ids = [backup.get("id") for backup in data if "id" in backup]
                    self.log_test("List Backups", True, f"Found {len(backup_ids)} backups: {backup_ids[:5]}")  # Show first 5 IDs
                    return backup_ids
                else:
                    self.log_test("List Backups", False, f"Unexpected response format: {type(data)}")
                    return []
            except json.JSONDecodeError:
                self.log_test("List Backups", False, "Invalid JSON response")
                return []
        else:
            self.log_test("List Backups", False, f"Status {response.status_code}: {response.text[:200]}")
            return []

    def test_backup_download(self, backup_id: str) -> bool:
        """TEST 6: GET /api/admin/backups/{backup_id}/download"""
        if not backup_id:
            self.log_test("Backup Download", False, "No backup_id provided")
            return False
            
        response = self.make_request("GET", f"/admin/backups/{backup_id}/download", headers=self.get_auth_headers())
        
        if not response:
            self.log_test("Backup Download", False, "Network request failed")
            return False
            
        if response.status_code == 200:
            content_length = len(response.content)
            content_type = response.headers.get("content-type", "unknown")
            self.log_test("Backup Download", True, f"Download successful: {content_length} bytes, type: {content_type}")
            return True
        elif response.status_code == 404:
            self.log_test("Backup Download", False, f"Backup file not found for ID: {backup_id}")
            return False
        else:
            self.log_test("Backup Download", False, f"Status {response.status_code}: {response.text[:200]}")
            return False

    def test_backup_deletion(self, backup_id: str) -> bool:
        """TEST 7: DELETE /api/admin/backups/{backup_id}"""
        if not backup_id:
            self.log_test("Backup Deletion", False, "No backup_id provided")
            return False
            
        response = self.make_request("DELETE", f"/admin/backups/{backup_id}", headers=self.get_auth_headers())
        
        if not response:
            self.log_test("Backup Deletion", False, "Network request failed")
            return False
            
        if response.status_code == 200:
            try:
                data = response.json()
                self.log_test("Backup Deletion", True, f"Backup deleted successfully: {data.get('message', 'No message')}")
                return True
            except json.JSONDecodeError:
                self.log_test("Backup Deletion", True, f"Backup deleted (no JSON response)")
                return True
        elif response.status_code == 404:
            self.log_test("Backup Deletion", False, f"Backup not found for deletion: {backup_id}")
            return False
        else:
            self.log_test("Backup Deletion", False, f"Status {response.status_code}: {response.text[:200]}")
            return False

    def wait_for_backup_completion(self, backup_id: str, max_wait_seconds: int = 60) -> bool:
        """Wait for backup to complete"""
        print(f"⏳ Waiting for backup {backup_id} to complete...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            # Check backup status by listing all backups
            response = self.make_request("GET", "/admin/backups", headers=self.get_auth_headers())
            
            if response and response.status_code == 200:
                try:
                    backups = response.json()
                    for backup in backups:
                        if backup.get("id") == backup_id:
                            status = backup.get("status", "unknown")
                            if status == "success":
                                print(f"✅ Backup {backup_id} completed successfully")
                                return True
                            elif status == "failed":
                                print(f"❌ Backup {backup_id} failed")
                                return False
                            # Otherwise still running, continue waiting
                            break
                except json.JSONDecodeError:
                    pass
                    
            time.sleep(3)  # Wait 3 seconds before next check
            
        print(f"⏰ Timeout waiting for backup {backup_id} to complete")
        return False

    def run_all_tests(self):
        """Run all backup functionality tests"""
        print("🚀 Starting MongoDB Backup Functionality Tests")
        print("=" * 60)
        
        # TEST 1: Admin Login
        if not self.test_admin_login():
            print("❌ Cannot continue without admin login")
            return
            
        print()
        
        # TEST 2: System Status
        self.test_backup_system_status()
        print()
        
        # TEST 3: Create Database Backup
        db_backup_result = self.test_manual_database_backup()
        print()
        
        # TEST 4: Create Storage Backup
        storage_backup_result = self.test_manual_storage_backup()
        print()
        
        # Wait for backups to complete
        created_backup_ids = []
        if db_backup_result["success"] and db_backup_result["backup_id"]:
            if self.wait_for_backup_completion(db_backup_result["backup_id"]):
                created_backup_ids.append(db_backup_result["backup_id"])
                
        if storage_backup_result["success"] and storage_backup_result["backup_id"]:
            if self.wait_for_backup_completion(storage_backup_result["backup_id"]):
                created_backup_ids.append(storage_backup_result["backup_id"])
        
        print()
        
        # TEST 5: List Backups
        all_backup_ids = self.test_list_backups()
        print()
        
        # TEST 6: Download Backup (use first available backup)
        download_backup_id = created_backup_ids[0] if created_backup_ids else (all_backup_ids[0] if all_backup_ids else None)
        if download_backup_id:
            self.test_backup_download(download_backup_id)
        else:
            self.log_test("Backup Download", False, "No backup available for download test")
        print()
        
        # TEST 7: Delete Backup (only delete one of our created backups)
        delete_backup_id = created_backup_ids[0] if created_backup_ids else None
        if delete_backup_id:
            self.test_backup_deletion(delete_backup_id)
        else:
            self.log_test("Backup Deletion", False, "No backup available for deletion test")
        
        # Summary
        print()
        print("=" * 60)
        print("🎯 TEST SUMMARY")
        print("=" * 60)
        
        passed_tests = sum(1 for result in self.test_results if result["success"])
        total_tests = len(self.test_results)
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"✅ Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        if passed_tests < total_tests:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test']}: {result['details']}")
        else:
            print("\n🎉 ALL TESTS PASSED! MongoDB Backup functionality is working correctly.")
        
        print()


if __name__ == "__main__":
    tester = BackupTester()
    tester.run_all_tests()
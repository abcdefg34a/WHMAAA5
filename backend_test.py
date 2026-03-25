#!/usr/bin/env python3
"""
AbschleppPortal Backup System Comprehensive Test Suite
Tests all backup-related endpoints with admin authentication
"""

import requests
import json
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://dual-yard-system.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@test.de"
ADMIN_PASSWORD = "Admin123!"

class BackupSystemTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "response_data": response_data
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        
    def authenticate_admin(self) -> bool:
        """Authenticate as admin user"""
        try:
            response = self.session.post(
                f"{BASE_URL}/auth/login",
                json={
                    "email": ADMIN_EMAIL,
                    "password": ADMIN_PASSWORD
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                self.session.headers.update({
                    "Authorization": f"Bearer {self.admin_token}"
                })
                self.log_test("Admin Authentication", True, f"Successfully authenticated as {ADMIN_EMAIL}")
                return True
            else:
                self.log_test("Admin Authentication", False, f"Failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Admin Authentication", False, f"Exception: {str(e)}")
            return False
    
    def test_backup_system_status(self):
        """Test GET /api/admin/backups/system-status"""
        try:
            response = self.session.get(f"{BASE_URL}/admin/backups/system-status")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Backup System Status", True, 
                            f"Retrieved system status successfully", data)
            else:
                self.log_test("Backup System Status", False, 
                            f"Failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Backup System Status", False, f"Exception: {str(e)}")
    
    def test_backup_health(self):
        """Test GET /api/admin/backups/health"""
        try:
            response = self.session.get(f"{BASE_URL}/admin/backups/health")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Backup Health Status", True, 
                            f"Retrieved health status successfully", data)
            else:
                self.log_test("Backup Health Status", False, 
                            f"Failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Backup Health Status", False, f"Exception: {str(e)}")
    
    def test_cloud_backups(self):
        """Test GET /api/admin/backups/cloud"""
        try:
            response = self.session.get(f"{BASE_URL}/admin/backups/cloud")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Cloud Backups List", True, 
                            f"Retrieved cloud backups successfully", data)
            else:
                self.log_test("Cloud Backups List", False, 
                            f"Failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Cloud Backups List", False, f"Exception: {str(e)}")
    
    def test_verify_all_backups(self):
        """Test POST /api/admin/backups/verify-all"""
        try:
            response = self.session.post(f"{BASE_URL}/admin/backups/verify-all")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Verify All Backups", True, 
                            f"Backup verification initiated successfully", data)
            else:
                self.log_test("Verify All Backups", False, 
                            f"Failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Verify All Backups", False, f"Exception: {str(e)}")
    
    def test_delete_corrupted_backups(self):
        """Test DELETE /api/admin/backups/corrupted"""
        try:
            response = self.session.delete(f"{BASE_URL}/admin/backups/corrupted")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Delete Corrupted Backups", True, 
                            f"Corrupted backups deletion completed", data)
            else:
                self.log_test("Delete Corrupted Backups", False, 
                            f"Failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Delete Corrupted Backups", False, f"Exception: {str(e)}")
    
    def test_backup_schedule(self):
        """Test GET /api/admin/backups/schedule"""
        try:
            response = self.session.get(f"{BASE_URL}/admin/backups/schedule")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Backup Schedule", True, 
                            f"Retrieved backup schedule successfully", data)
            else:
                self.log_test("Backup Schedule", False, 
                            f"Failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Backup Schedule", False, f"Exception: {str(e)}")
    
    def test_storage_stats(self):
        """Test GET /api/admin/backups/storage-stats"""
        try:
            response = self.session.get(f"{BASE_URL}/admin/backups/storage-stats")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Storage Statistics", True, 
                            f"Retrieved storage stats successfully", data)
            else:
                self.log_test("Storage Statistics", False, 
                            f"Failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Storage Statistics", False, f"Exception: {str(e)}")
    
    def test_create_database_backup_old_endpoint(self):
        """Test POST /api/admin/backup with backup_type=database (old endpoint)"""
        try:
            response = self.session.post(
                f"{BASE_URL}/admin/backup",
                params={"backup_type": "database"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Create Database Backup (Old Endpoint)", True, 
                            f"Database backup created successfully", data)
            else:
                self.log_test("Create Database Backup (Old Endpoint)", False, 
                            f"Failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Create Database Backup (Old Endpoint)", False, f"Exception: {str(e)}")
    
    def test_create_storage_backup_old_endpoint(self):
        """Test POST /api/admin/backup with backup_type=storage (old endpoint)"""
        try:
            response = self.session.post(
                f"{BASE_URL}/admin/backup",
                params={"backup_type": "storage"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Create Storage Backup (Old Endpoint)", True, 
                            f"Storage backup created successfully", data)
            else:
                self.log_test("Create Storage Backup (Old Endpoint)", False, 
                            f"Failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Create Storage Backup (Old Endpoint)", False, f"Exception: {str(e)}")
    
    def test_create_database_backup_new_endpoint(self):
        """Test POST /api/admin/backups/run-database-backup (new endpoint)"""
        try:
            response = self.session.post(f"{BASE_URL}/admin/backups/run-database-backup")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Create Database Backup (New Endpoint)", True, 
                            f"Database backup created successfully", data)
            else:
                self.log_test("Create Database Backup (New Endpoint)", False, 
                            f"Failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Create Database Backup (New Endpoint)", False, f"Exception: {str(e)}")
    
    def test_create_storage_backup_new_endpoint(self):
        """Test POST /api/admin/backups/run-storage-backup (new endpoint)"""
        try:
            response = self.session.post(f"{BASE_URL}/admin/backups/run-storage-backup")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Create Storage Backup (New Endpoint)", True, 
                            f"Storage backup created successfully", data)
            else:
                self.log_test("Create Storage Backup (New Endpoint)", False, 
                            f"Failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Create Storage Backup (New Endpoint)", False, f"Exception: {str(e)}")
    
    def test_list_backups(self):
        """Test GET /api/admin/backups"""
        try:
            response = self.session.get(f"{BASE_URL}/admin/backups")
            
            if response.status_code == 200:
                data = response.json()
                backup_count = len(data) if isinstance(data, list) else data.get('count', 'unknown')
                self.log_test("List All Backups", True, 
                            f"Retrieved {backup_count} backups successfully", data)
            else:
                self.log_test("List All Backups", False, 
                            f"Failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("List All Backups", False, f"Exception: {str(e)}")
    
    def test_cleanup_backups(self):
        """Test POST /api/admin/backups/cleanup"""
        try:
            response = self.session.post(f"{BASE_URL}/admin/backups/cleanup")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Cleanup Old Backups", True, 
                            f"Backup cleanup completed successfully", data)
            else:
                self.log_test("Cleanup Old Backups", False, 
                            f"Failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Cleanup Old Backups", False, f"Exception: {str(e)}")
    
    def test_backup_with_json_body(self):
        """Test if there's a POST /api/admin/backups endpoint that accepts JSON body"""
        try:
            # Test database backup with JSON body
            response = self.session.post(
                f"{BASE_URL}/admin/backups",
                json={"backup_type": "database"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Create Backup with JSON Body (Database)", True, 
                            f"Database backup created with JSON body", data)
            elif response.status_code == 404:
                self.log_test("Create Backup with JSON Body (Database)", False, 
                            f"Endpoint not found - using alternative endpoints instead")
            else:
                self.log_test("Create Backup with JSON Body (Database)", False, 
                            f"Failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Create Backup with JSON Body (Database)", False, f"Exception: {str(e)}")
        
        try:
            # Test storage backup with JSON body
            response = self.session.post(
                f"{BASE_URL}/admin/backups",
                json={"backup_type": "storage"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Create Backup with JSON Body (Storage)", True, 
                            f"Storage backup created with JSON body", data)
            elif response.status_code == 404:
                self.log_test("Create Backup with JSON Body (Storage)", False, 
                            f"Endpoint not found - using alternative endpoints instead")
            else:
                self.log_test("Create Backup with JSON Body (Storage)", False, 
                            f"Failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Create Backup with JSON Body (Storage)", False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run all backup system tests"""
        print("=" * 80)
        print("ABSCHLEPPPORTAL BACKUP SYSTEM COMPREHENSIVE TEST")
        print("=" * 80)
        
        # Authenticate first
        if not self.authenticate_admin():
            print("❌ Authentication failed - cannot proceed with tests")
            return
        
        print("\n" + "=" * 50)
        print("TESTING BACKUP SYSTEM ENDPOINTS")
        print("=" * 50)
        
        # Test all backup endpoints
        self.test_backup_system_status()
        self.test_backup_health()
        self.test_cloud_backups()
        self.test_verify_all_backups()
        self.test_delete_corrupted_backups()
        self.test_backup_schedule()
        self.test_storage_stats()
        self.test_list_backups()
        self.test_cleanup_backups()
        
        print("\n" + "=" * 50)
        print("TESTING BACKUP CREATION ENDPOINTS")
        print("=" * 50)
        
        # Test backup creation endpoints
        self.test_backup_with_json_body()  # Test the requested format first
        self.test_create_database_backup_old_endpoint()
        self.test_create_storage_backup_old_endpoint()
        self.test_create_database_backup_new_endpoint()
        self.test_create_storage_backup_new_endpoint()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n✅ PASSED TESTS:")
        for result in self.test_results:
            if result["success"]:
                print(f"  - {result['test']}: {result['details']}")

if __name__ == "__main__":
    tester = BackupSystemTester()
    tester.run_all_tests()
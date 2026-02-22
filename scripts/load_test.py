#!/usr/bin/env python3
"""
Lasttest für Abschlepp-Manager
Testet: 400 Behörden, 800 Abschleppdienste, 800 gleichzeitige Aufträge
"""

import asyncio
import aiohttp
import time
import random
import string
import json
from datetime import datetime
from collections import defaultdict

API_URL = "http://localhost:8001/api"

# Test configuration
NUM_AUTHORITIES = 400
NUM_TOWING_SERVICES = 800
NUM_JOBS = 800

# Results tracking
results = defaultdict(lambda: {"success": 0, "failed": 0, "times": []})

def random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def random_plate():
    letters = ''.join(random.choices(string.ascii_uppercase, k=2))
    numbers = ''.join(random.choices(string.digits, k=4))
    return f"TEST-{letters}{numbers}"

async def register_authority(session, index):
    """Register a single authority"""
    start = time.time()
    try:
        data = {
            "email": f"test_authority_{index}_{random_string(4)}@loadtest.de",
            "password": "TestPass123!",
            "name": f"Test Authority {index}",
            "role": "authority",
            "authority_name": f"Ordnungsamt Test {index}",
            "department": "Abteilung A"
        }
        async with session.post(f"{API_URL}/auth/register", json=data) as resp:
            elapsed = time.time() - start
            results["authority_register"]["times"].append(elapsed)
            # 202 is success (needs approval), 200 is also success
            if resp.status in [200, 201, 202]:
                results["authority_register"]["success"] += 1
                return True
            else:
                results["authority_register"]["failed"] += 1
                return False
    except Exception as e:
        results["authority_register"]["failed"] += 1
        return False

async def register_towing_service(session, index):
    """Register a single towing service"""
    start = time.time()
    try:
        data = {
            "email": f"test_towing_{index}_{random_string(4)}@loadtest.de",
            "password": "TestPass123!",
            "name": f"Test Towing {index}",
            "role": "towing_service",
            "company_name": f"Abschleppdienst Test {index}",
            "phone": "+49123456789",
            "address": f"Teststraße {index}",
            "yard_address": f"Hofstraße {index}",
            "opening_hours": "Mo-Fr 08:00-18:00",
            "tow_cost": 150.0,
            "daily_cost": 20.0,
            "business_license": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        }
        async with session.post(f"{API_URL}/auth/register", json=data) as resp:
            elapsed = time.time() - start
            results["towing_register"]["times"].append(elapsed)
            if resp.status in [200, 201, 202]:
                results["towing_register"]["success"] += 1
                return True
            else:
                results["towing_register"]["failed"] += 1
                return False
    except Exception as e:
        results["towing_register"]["failed"] += 1
        return False

async def login_admin(session):
    """Login as admin and return token"""
    try:
        async with session.post(f"{API_URL}/auth/login", json={
            "email": "admin@test.de",
            "password": "Admin123!"
        }) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("access_token")
    except:
        pass
    return None

async def approve_user(session, token, user_id, user_type):
    """Approve a pending user"""
    start = time.time()
    try:
        headers = {"Authorization": f"Bearer {token}"}
        endpoint = f"{API_URL}/admin/approve-service/{user_id}" if user_type == "towing" else f"{API_URL}/admin/approve-authority/{user_id}"
        async with session.post(endpoint, json={"approved": True}, headers=headers) as resp:
            elapsed = time.time() - start
            results["approve"]["times"].append(elapsed)
            if resp.status == 200:
                results["approve"]["success"] += 1
                return True
            else:
                results["approve"]["failed"] += 1
                return False
    except Exception as e:
        results["approve"]["failed"] += 1
        return False

async def create_job(session, token, index, service_id=None):
    """Create a single job"""
    start = time.time()
    try:
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "license_plate": random_plate(),
            "vin": f"WDB{random_string(14).upper()}",
            "tow_reason": f"Lasttest Auftrag {index}",
            "location_address": f"Teststraße {index}, Berlin",
            "location_lat": 52.52 + random.uniform(-0.1, 0.1),
            "location_lng": 13.405 + random.uniform(-0.1, 0.1),
            "photos": [],
            "notes": f"Automatisch generierter Testauftrag #{index}",
            "assigned_service_id": service_id
        }
        async with session.post(f"{API_URL}/jobs", json=data, headers=headers) as resp:
            elapsed = time.time() - start
            results["create_job"]["times"].append(elapsed)
            if resp.status in [200, 201]:
                results["create_job"]["success"] += 1
                return True
            else:
                text = await resp.text()
                results["create_job"]["failed"] += 1
                return False
    except Exception as e:
        results["create_job"]["failed"] += 1
        return False

async def get_jobs(session, token):
    """Get jobs list"""
    start = time.time()
    try:
        headers = {"Authorization": f"Bearer {token}"}
        async with session.get(f"{API_URL}/jobs", headers=headers) as resp:
            elapsed = time.time() - start
            results["get_jobs"]["times"].append(elapsed)
            if resp.status == 200:
                results["get_jobs"]["success"] += 1
                return await resp.json()
            else:
                results["get_jobs"]["failed"] += 1
                return []
    except Exception as e:
        results["get_jobs"]["failed"] += 1
        return []

def print_results():
    """Print test results"""
    print("\n" + "="*70)
    print("LASTTEST ERGEBNISSE")
    print("="*70)
    
    for operation, data in results.items():
        total = data["success"] + data["failed"]
        success_rate = (data["success"] / total * 100) if total > 0 else 0
        avg_time = sum(data["times"]) / len(data["times"]) if data["times"] else 0
        max_time = max(data["times"]) if data["times"] else 0
        min_time = min(data["times"]) if data["times"] else 0
        
        print(f"\n{operation.upper()}:")
        print(f"  Erfolgreich: {data['success']}/{total} ({success_rate:.1f}%)")
        print(f"  Durchschnittliche Zeit: {avg_time*1000:.1f}ms")
        print(f"  Min/Max Zeit: {min_time*1000:.1f}ms / {max_time*1000:.1f}ms")
    
    print("\n" + "="*70)

async def run_load_test():
    """Run the complete load test"""
    print("\n" + "="*70)
    print("ABSCHLEPP-MANAGER LASTTEST")
    print(f"Konfiguration: {NUM_AUTHORITIES} Behörden, {NUM_TOWING_SERVICES} Abschleppdienste, {NUM_JOBS} Aufträge")
    print("="*70)
    
    connector = aiohttp.TCPConnector(limit=100, limit_per_host=100)
    timeout = aiohttp.ClientTimeout(total=60)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        
        # Step 1: Login as admin
        print("\n[1/6] Admin Login...")
        admin_token = await login_admin(session)
        if not admin_token:
            print("❌ Admin-Login fehlgeschlagen!")
            return
        print("✅ Admin eingeloggt")
        
        # Step 2: Register authorities in batches
        print(f"\n[2/6] Registriere {NUM_AUTHORITIES} Behörden...")
        start = time.time()
        batch_size = 50
        for i in range(0, NUM_AUTHORITIES, batch_size):
            batch = [register_authority(session, j) for j in range(i, min(i + batch_size, NUM_AUTHORITIES))]
            await asyncio.gather(*batch)
            print(f"  Fortschritt: {min(i + batch_size, NUM_AUTHORITIES)}/{NUM_AUTHORITIES}", end="\r")
        print(f"\n  Zeit: {time.time() - start:.2f}s")
        
        # Step 3: Register towing services in batches
        print(f"\n[3/6] Registriere {NUM_TOWING_SERVICES} Abschleppdienste...")
        start = time.time()
        for i in range(0, NUM_TOWING_SERVICES, batch_size):
            batch = [register_towing_service(session, j) for j in range(i, min(i + batch_size, NUM_TOWING_SERVICES))]
            await asyncio.gather(*batch)
            print(f"  Fortschritt: {min(i + batch_size, NUM_TOWING_SERVICES)}/{NUM_TOWING_SERVICES}", end="\r")
        print(f"\n  Zeit: {time.time() - start:.2f}s")
        
        # Step 4: Approve all pending users
        print(f"\n[4/6] Genehmige ausstehende Benutzer...")
        start = time.time()
        
        # Get pending authorities
        headers = {"Authorization": f"Bearer {admin_token}"}
        async with session.get(f"{API_URL}/admin/pending-authorities", headers=headers) as resp:
            pending_authorities = await resp.json() if resp.status == 200 else []
        
        # Get pending towing services
        async with session.get(f"{API_URL}/admin/pending-services", headers=headers) as resp:
            pending_services = await resp.json() if resp.status == 200 else []
        
        print(f"  Ausstehende Behörden: {len(pending_authorities)}")
        print(f"  Ausstehende Abschleppdienste: {len(pending_services)}")
        
        # Approve in batches
        all_pending = [(u["id"], "authority") for u in pending_authorities] + [(u["id"], "towing") for u in pending_services]
        for i in range(0, len(all_pending), batch_size):
            batch = [approve_user(session, admin_token, uid, utype) for uid, utype in all_pending[i:i+batch_size]]
            await asyncio.gather(*batch)
            print(f"  Genehmigt: {min(i + batch_size, len(all_pending))}/{len(all_pending)}", end="\r")
        print(f"\n  Zeit: {time.time() - start:.2f}s")
        
        # Step 5: Get approved services for job assignment
        print(f"\n[5/6] Lade genehmigte Dienste...")
        async with session.get(f"{API_URL}/admin/users", headers=headers) as resp:
            if resp.status == 200:
                all_users = await resp.json()
                approved_services = [u for u in all_users if u["role"] == "towing_service" and u.get("approval_status") == "approved"]
                approved_authorities = [u for u in all_users if u["role"] == "authority" and u.get("approval_status") == "approved"]
                print(f"  Genehmigte Abschleppdienste: {len(approved_services)}")
                print(f"  Genehmigte Behörden: {len(approved_authorities)}")
        
        # Step 6: Create jobs using authority accounts
        if approved_authorities and approved_services:
            print(f"\n[6/6] Erstelle {NUM_JOBS} Aufträge gleichzeitig...")
            start = time.time()
            
            # Login as first approved authority
            auth_email = approved_authorities[0]["email"]
            async with session.post(f"{API_URL}/auth/login", json={
                "email": auth_email,
                "password": "TestPass123!"
            }) as resp:
                if resp.status == 200:
                    auth_data = await resp.json()
                    auth_token = auth_data["access_token"]
                    
                    # Create jobs in batches
                    service_ids = [s["id"] for s in approved_services]
                    for i in range(0, NUM_JOBS, batch_size):
                        batch = [
                            create_job(session, auth_token, j, random.choice(service_ids) if service_ids else None) 
                            for j in range(i, min(i + batch_size, NUM_JOBS))
                        ]
                        await asyncio.gather(*batch)
                        print(f"  Fortschritt: {min(i + batch_size, NUM_JOBS)}/{NUM_JOBS}", end="\r")
                    print(f"\n  Zeit: {time.time() - start:.2f}s")
                else:
                    print(f"  ❌ Behörden-Login fehlgeschlagen: {resp.status}")
        else:
            print("\n[6/6] ⚠️ Keine genehmigten Benutzer für Aufträge verfügbar")
        
        # Step 7: Test job retrieval
        print(f"\n[BONUS] Teste Auftrags-Abruf (10x parallel)...")
        start = time.time()
        if 'auth_token' in dir():
            batch = [get_jobs(session, auth_token) for _ in range(10)]
            job_results = await asyncio.gather(*batch)
            print(f"  Zeit: {time.time() - start:.2f}s")
            if job_results and job_results[0]:
                print(f"  Aufträge in DB: {len(job_results[0])}")
    
    # Print final results
    print_results()
    
    # Summary
    print("\n" + "="*70)
    print("ZUSAMMENFASSUNG")
    print("="*70)
    total_success = sum(d["success"] for d in results.values())
    total_failed = sum(d["failed"] for d in results.values())
    total_ops = total_success + total_failed
    print(f"Gesamt-Operationen: {total_ops}")
    print(f"Erfolgreich: {total_success} ({total_success/total_ops*100:.1f}%)" if total_ops > 0 else "")
    print(f"Fehlgeschlagen: {total_failed} ({total_failed/total_ops*100:.1f}%)" if total_ops > 0 else "")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(run_load_test())

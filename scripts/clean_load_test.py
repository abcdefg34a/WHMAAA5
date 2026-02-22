#!/usr/bin/env python3
"""
Sauberer Lasttest - erstellt 100 Behörden, 200 Abschleppdienste, 200 Aufträge
"""

import asyncio
import aiohttp
import time
import random
import string
from collections import defaultdict

API_URL = "http://localhost:8001/api"

results = defaultdict(lambda: {"success": 0, "failed": 0, "times": []})
TEST_PASSWORD = "LoadTest123!"
created_authorities = []
created_services = []

def random_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))

def random_plate():
    return f"LT-{''.join(random.choices(string.ascii_uppercase, k=2))}{''.join(random.choices(string.digits, k=4))}"

async def register_and_track(session, role, index):
    """Register user and track credentials"""
    start = time.time()
    email = f"loadtest_{role}_{index}_{random_id()}@test.de"
    
    try:
        if role == "authority":
            data = {
                "email": email,
                "password": TEST_PASSWORD,
                "name": f"LT Auth {index}",
                "role": "authority",
                "authority_name": f"Amt {index}",
                "department": "Test"
            }
        else:
            data = {
                "email": email,
                "password": TEST_PASSWORD,
                "name": f"LT Tow {index}",
                "role": "towing_service",
                "company_name": f"Abschlepp {index}",
                "phone": "+49123456789",
                "address": f"Str {index}",
                "yard_address": f"Hof {index}",
                "opening_hours": "24/7",
                "tow_cost": 150.0,
                "daily_cost": 20.0,
                "business_license": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            }
        
        async with session.post(f"{API_URL}/auth/register", json=data) as resp:
            elapsed = time.time() - start
            results[f"{role}_register"]["times"].append(elapsed)
            
            if resp.status in [200, 201, 202]:
                results[f"{role}_register"]["success"] += 1
                if role == "authority":
                    created_authorities.append(email)
                else:
                    created_services.append(email)
                return True
            else:
                results[f"{role}_register"]["failed"] += 1
                return False
    except Exception as e:
        results[f"{role}_register"]["failed"] += 1
        return False

async def approve_all(session, admin_token):
    """Approve all pending users"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Get pending
    async with session.get(f"{API_URL}/admin/pending-authorities", headers=headers) as resp:
        pending_auth = await resp.json() if resp.status == 200 else []
    async with session.get(f"{API_URL}/admin/pending-services", headers=headers) as resp:
        pending_tow = await resp.json() if resp.status == 200 else []
    
    print(f"  Genehmige {len(pending_auth)} Behörden + {len(pending_tow)} Abschleppdienste...")
    
    # Approve authorities
    for u in pending_auth:
        start = time.time()
        async with session.post(f"{API_URL}/admin/approve-authority/{u['id']}", json={"approved": True}, headers=headers) as resp:
            results["approve"]["times"].append(time.time() - start)
            if resp.status == 200:
                results["approve"]["success"] += 1
            else:
                results["approve"]["failed"] += 1
    
    # Approve services
    for u in pending_tow:
        start = time.time()
        async with session.post(f"{API_URL}/admin/approve-service/{u['id']}", json={"approved": True}, headers=headers) as resp:
            results["approve"]["times"].append(time.time() - start)
            if resp.status == 200:
                results["approve"]["success"] += 1
            else:
                results["approve"]["failed"] += 1

async def create_job(session, auth_token, index, service_id):
    """Create a job"""
    start = time.time()
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        data = {
            "license_plate": random_plate(),
            "tow_reason": f"Lasttest Auftrag #{index}",
            "location_address": f"Teststraße {index}, Berlin",
            "location_lat": 52.52 + random.uniform(-0.1, 0.1),
            "location_lng": 13.405 + random.uniform(-0.1, 0.1),
            "photos": [],
            "assigned_service_id": service_id
        }
        async with session.post(f"{API_URL}/jobs", json=data, headers=headers) as resp:
            elapsed = time.time() - start
            results["create_job"]["times"].append(elapsed)
            if resp.status in [200, 201]:
                results["create_job"]["success"] += 1
            else:
                results["create_job"]["failed"] += 1
    except:
        results["create_job"]["failed"] += 1

async def main():
    NUM_AUTH = 100
    NUM_TOW = 200
    NUM_JOBS = 200
    
    print("="*60)
    print(f"LASTTEST: {NUM_AUTH} Behörden, {NUM_TOW} Abschlepper, {NUM_JOBS} Jobs")
    print("="*60)
    
    connector = aiohttp.TCPConnector(limit=30)
    timeout = aiohttp.ClientTimeout(total=60)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # 1. Admin login
        print("\n[1] Admin Login...")
        async with session.post(f"{API_URL}/auth/login", json={"email": "admin@test.de", "password": "Admin123!"}) as resp:
            if resp.status != 200:
                print("❌ Fehlgeschlagen!")
                return
            admin_token = (await resp.json())["access_token"]
        print("✅ OK")
        
        # 2. Register authorities (sequentially in small batches)
        print(f"\n[2] Registriere {NUM_AUTH} Behörden...")
        start = time.time()
        for i in range(0, NUM_AUTH, 20):
            batch = [register_and_track(session, "authority", j) for j in range(i, min(i+20, NUM_AUTH))]
            await asyncio.gather(*batch)
            print(f"  {min(i+20, NUM_AUTH)}/{NUM_AUTH}", end="\r")
        print(f"\n  ✅ {results['authority_register']['success']} OK in {time.time()-start:.1f}s")
        
        # 3. Register towing services
        print(f"\n[3] Registriere {NUM_TOW} Abschleppdienste...")
        start = time.time()
        for i in range(0, NUM_TOW, 20):
            batch = [register_and_track(session, "towing_service", j) for j in range(i, min(i+20, NUM_TOW))]
            await asyncio.gather(*batch)
            print(f"  {min(i+20, NUM_TOW)}/{NUM_TOW}", end="\r")
        print(f"\n  ✅ {results['towing_service_register']['success']} OK in {time.time()-start:.1f}s")
        
        # 4. Approve all
        print(f"\n[4] Genehmige alle Benutzer...")
        start = time.time()
        await approve_all(session, admin_token)
        print(f"  ✅ {results['approve']['success']} genehmigt in {time.time()-start:.1f}s")
        
        # 5. Get approved service IDs
        headers = {"Authorization": f"Bearer {admin_token}"}
        async with session.get(f"{API_URL}/admin/users", headers=headers) as resp:
            users = await resp.json() if resp.status == 200 else []
        
        approved_auth = [u for u in users if u["role"] == "authority" and u.get("approval_status") == "approved"]
        approved_tow = [u for u in users if u["role"] == "towing_service" and u.get("approval_status") == "approved"]
        
        print(f"\n[5] Verfügbar: {len(approved_auth)} Behörden, {len(approved_tow)} Abschleppdienste")
        
        if created_authorities and approved_tow:
            # 6. Login as first created authority
            auth_email = created_authorities[0]
            print(f"\n[6] Login als Behörde: {auth_email}")
            
            async with session.post(f"{API_URL}/auth/login", json={"email": auth_email, "password": TEST_PASSWORD}) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    print(f"  ❌ Login fehlgeschlagen: {resp.status} - {err}")
                    return
                auth_token = (await resp.json())["access_token"]
            print("  ✅ OK")
            
            # 7. Create jobs
            print(f"\n[7] Erstelle {NUM_JOBS} Aufträge...")
            start = time.time()
            service_ids = [s["id"] for s in approved_tow]
            
            for i in range(0, NUM_JOBS, 50):
                batch = [create_job(session, auth_token, j, random.choice(service_ids)) for j in range(i, min(i+50, NUM_JOBS))]
                await asyncio.gather(*batch)
                print(f"  {min(i+50, NUM_JOBS)}/{NUM_JOBS}", end="\r")
            
            print(f"\n  ✅ {results['create_job']['success']} erstellt in {time.time()-start:.1f}s")
    
    # Results
    print("\n" + "="*60)
    print("ERGEBNISSE")
    print("="*60)
    
    for op, data in sorted(results.items()):
        total = data["success"] + data["failed"]
        if total == 0:
            continue
        rate = (data["success"] / total * 100)
        avg_ms = (sum(data["times"]) / len(data["times"]) * 1000) if data["times"] else 0
        max_ms = max(data["times"]) * 1000 if data["times"] else 0
        print(f"{op:25s}: {data['success']:4d}/{total:4d} ({rate:5.1f}%) | Ø {avg_ms:6.0f}ms | Max {max_ms:6.0f}ms")
    
    print("="*60)
    total_ok = sum(d["success"] for d in results.values())
    total_fail = sum(d["failed"] for d in results.values())
    print(f"GESAMT: {total_ok} erfolgreich, {total_fail} fehlgeschlagen")
    
    if total_fail == 0:
        print("\n🎉 ALLE TESTS BESTANDEN!")
    else:
        print(f"\n⚠️  {total_fail} Fehler aufgetreten")
    
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Schneller Lasttest für Abschlepp-Manager
Testet: 50 Behörden, 100 Abschleppdienste, 100 Aufträge
"""

import asyncio
import aiohttp
import time
import random
import string
from collections import defaultdict

API_URL = "http://localhost:8001/api"

# Kleinere Test-Konfiguration
NUM_AUTHORITIES = 50
NUM_TOWING_SERVICES = 100
NUM_JOBS = 100

results = defaultdict(lambda: {"success": 0, "failed": 0, "times": []})

def random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def random_plate():
    letters = ''.join(random.choices(string.ascii_uppercase, k=2))
    numbers = ''.join(random.choices(string.digits, k=4))
    return f"LT-{letters}{numbers}"

async def register_authority(session, index):
    start = time.time()
    try:
        data = {
            "email": f"lt_auth_{index}_{random_string(4)}@test.de",
            "password": "TestPass123!",
            "name": f"LT Authority {index}",
            "role": "authority",
            "authority_name": f"Ordnungsamt LT {index}",
            "department": "Test"
        }
        async with session.post(f"{API_URL}/auth/register", json=data) as resp:
            elapsed = time.time() - start
            results["auth_register"]["times"].append(elapsed)
            if resp.status in [200, 201, 202]:
                results["auth_register"]["success"] += 1
            else:
                results["auth_register"]["failed"] += 1
    except:
        results["auth_register"]["failed"] += 1

async def register_towing(session, index):
    start = time.time()
    try:
        data = {
            "email": f"lt_tow_{index}_{random_string(4)}@test.de",
            "password": "TestPass123!",
            "name": f"LT Towing {index}",
            "role": "towing_service",
            "company_name": f"Abschlepp LT {index}",
            "phone": "+49123456789",
            "address": f"Straße {index}",
            "yard_address": f"Hof {index}",
            "opening_hours": "Mo-Fr 08-18",
            "tow_cost": 150.0,
            "daily_cost": 20.0,
            "business_license": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        }
        async with session.post(f"{API_URL}/auth/register", json=data) as resp:
            elapsed = time.time() - start
            results["tow_register"]["times"].append(elapsed)
            if resp.status in [200, 201, 202]:
                results["tow_register"]["success"] += 1
            else:
                results["tow_register"]["failed"] += 1
    except:
        results["tow_register"]["failed"] += 1

async def approve_user(session, token, user_id, endpoint):
    start = time.time()
    try:
        headers = {"Authorization": f"Bearer {token}"}
        async with session.post(f"{API_URL}/{endpoint}/{user_id}", json={"approved": True}, headers=headers) as resp:
            elapsed = time.time() - start
            results["approve"]["times"].append(elapsed)
            if resp.status == 200:
                results["approve"]["success"] += 1
            else:
                results["approve"]["failed"] += 1
    except:
        results["approve"]["failed"] += 1

async def create_job(session, token, index, service_id):
    start = time.time()
    try:
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "license_plate": random_plate(),
            "tow_reason": f"Lasttest {index}",
            "location_address": f"Teststr. {index}, Berlin",
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
    print("="*60)
    print("LASTTEST: 50 Behörden, 100 Abschlepper, 100 Aufträge")
    print("="*60)
    
    connector = aiohttp.TCPConnector(limit=50)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Admin login
        print("\n[1] Admin Login...")
        async with session.post(f"{API_URL}/auth/login", json={"email": "admin@test.de", "password": "Admin123!"}) as resp:
            if resp.status != 200:
                print("❌ Admin Login fehlgeschlagen!")
                return
            admin_data = await resp.json()
            admin_token = admin_data["access_token"]
        print("✅ OK")
        
        # Register authorities
        print(f"\n[2] Registriere {NUM_AUTHORITIES} Behörden...")
        start = time.time()
        tasks = [register_authority(session, i) for i in range(NUM_AUTHORITIES)]
        await asyncio.gather(*tasks)
        print(f"✅ {results['auth_register']['success']} erfolgreich in {time.time()-start:.1f}s")
        
        # Register towing services
        print(f"\n[3] Registriere {NUM_TOWING_SERVICES} Abschleppdienste...")
        start = time.time()
        tasks = [register_towing(session, i) for i in range(NUM_TOWING_SERVICES)]
        await asyncio.gather(*tasks)
        print(f"✅ {results['tow_register']['success']} erfolgreich in {time.time()-start:.1f}s")
        
        # Get pending users
        print("\n[4] Genehmige Benutzer...")
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        async with session.get(f"{API_URL}/admin/pending-authorities", headers=headers) as resp:
            pending_auth = await resp.json() if resp.status == 200 else []
        async with session.get(f"{API_URL}/admin/pending-services", headers=headers) as resp:
            pending_tow = await resp.json() if resp.status == 200 else []
        
        print(f"  Ausstehend: {len(pending_auth)} Behörden, {len(pending_tow)} Abschleppdienste")
        
        start = time.time()
        tasks = []
        for u in pending_auth[:50]:  # Max 50
            tasks.append(approve_user(session, admin_token, u["id"], "admin/approve-authority"))
        for u in pending_tow[:100]:  # Max 100
            tasks.append(approve_user(session, admin_token, u["id"], "admin/approve-service"))
        await asyncio.gather(*tasks)
        print(f"✅ {results['approve']['success']} genehmigt in {time.time()-start:.1f}s")
        
        # Get approved users
        async with session.get(f"{API_URL}/admin/users", headers=headers) as resp:
            users = await resp.json() if resp.status == 200 else []
        
        approved_auth = [u for u in users if u["role"] == "authority" and u.get("approval_status") == "approved"]
        approved_tow = [u for u in users if u["role"] == "towing_service" and u.get("approval_status") == "approved"]
        
        print(f"\n[5] Genehmigte Benutzer: {len(approved_auth)} Behörden, {len(approved_tow)} Abschleppdienste")
        
        if approved_auth and approved_tow:
            # Login as authority
            auth_email = approved_auth[0]["email"]
            async with session.post(f"{API_URL}/auth/login", json={"email": auth_email, "password": "TestPass123!"}) as resp:
                if resp.status == 200:
                    auth_data = await resp.json()
                    auth_token = auth_data["access_token"]
                    
                    # Create jobs
                    print(f"\n[6] Erstelle {NUM_JOBS} Aufträge gleichzeitig...")
                    start = time.time()
                    service_ids = [s["id"] for s in approved_tow]
                    tasks = [create_job(session, auth_token, i, random.choice(service_ids)) for i in range(NUM_JOBS)]
                    await asyncio.gather(*tasks)
                    print(f"✅ {results['create_job']['success']} erstellt in {time.time()-start:.1f}s")
                else:
                    print(f"❌ Behörden-Login fehlgeschlagen: {resp.status}")
    
    # Results
    print("\n" + "="*60)
    print("ERGEBNISSE")
    print("="*60)
    
    for op, data in results.items():
        total = data["success"] + data["failed"]
        rate = (data["success"] / total * 100) if total > 0 else 0
        avg_ms = (sum(data["times"]) / len(data["times"]) * 1000) if data["times"] else 0
        print(f"{op}: {data['success']}/{total} ({rate:.0f}%) - Ø {avg_ms:.0f}ms")
    
    print("\n" + "="*60)
    total_ok = sum(d["success"] for d in results.values())
    total_fail = sum(d["failed"] for d in results.values())
    print(f"GESAMT: {total_ok} OK, {total_fail} Fehler")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())

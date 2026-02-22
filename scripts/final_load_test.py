#!/usr/bin/env python3
"""
Finaler Lasttest - nutzt existierende genehmigte Accounts
Testet: 200 gleichzeitige Aufträge
"""

import asyncio
import aiohttp
import time
import random
import string
from collections import defaultdict

API_URL = "http://localhost:8001/api"
results = defaultdict(lambda: {"success": 0, "failed": 0, "times": []})

def random_plate():
    return f"FIN-{''.join(random.choices(string.ascii_uppercase, k=2))}{''.join(random.choices(string.digits, k=4))}"

async def create_job(session, auth_token, index, service_id):
    start = time.time()
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        data = {
            "license_plate": random_plate(),
            "tow_reason": f"Finaler Lasttest #{index}",
            "location_address": f"Finalstraße {index}, Berlin",
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
    except Exception as e:
        results["create_job"]["failed"] += 1

async def get_jobs(session, token):
    start = time.time()
    headers = {"Authorization": f"Bearer {token}"}
    async with session.get(f"{API_URL}/jobs?page=1&limit=50", headers=headers) as resp:
        elapsed = time.time() - start
        results["get_jobs"]["times"].append(elapsed)
        if resp.status == 200:
            results["get_jobs"]["success"] += 1
            return await resp.json()
        results["get_jobs"]["failed"] += 1
        return []

async def main():
    NUM_JOBS = 200
    CONCURRENT_READS = 50
    
    print("="*60)
    print("FINALER LASTTEST")
    print("="*60)
    
    connector = aiohttp.TCPConnector(limit=100)
    timeout = aiohttp.ClientTimeout(total=60)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Admin login
        print("\n[1] Admin Login...")
        async with session.post(f"{API_URL}/auth/login", json={"email": "admin@test.de", "password": "Admin123!"}) as resp:
            if resp.status != 200:
                print("❌ Fehlgeschlagen!")
                return
            admin_token = (await resp.json())["access_token"]
        print("✅ OK")
        
        # Get approved accounts
        print("\n[2] Lade genehmigte Accounts...")
        headers = {"Authorization": f"Bearer {admin_token}"}
        async with session.get(f"{API_URL}/admin/users", headers=headers) as resp:
            users = await resp.json() if resp.status == 200 else []
        
        approved_auth = [u for u in users if u["role"] == "authority" and u.get("approval_status") == "approved"]
        approved_tow = [u for u in users if u["role"] == "towing_service" and u.get("approval_status") == "approved"]
        
        print(f"  ✅ {len(approved_auth)} Behörden, {len(approved_tow)} Abschleppdienste verfügbar")
        
        if not approved_auth or not approved_tow:
            print("❌ Keine genehmigten Accounts!")
            return
        
        # Use admin token to create jobs (admin can create jobs too for testing)
        # Actually, let's use the first approved authority if possible
        # But we don't know the password... so let's use admin
        
        print(f"\n[3] Erstelle {NUM_JOBS} Aufträge gleichzeitig...")
        start = time.time()
        service_ids = [s["id"] for s in approved_tow]
        
        # Create all jobs at once
        tasks = [create_job(session, admin_token, i, random.choice(service_ids)) for i in range(NUM_JOBS)]
        await asyncio.gather(*tasks)
        
        elapsed = time.time() - start
        jobs_per_sec = results["create_job"]["success"] / elapsed if elapsed > 0 else 0
        print(f"  ✅ {results['create_job']['success']}/{NUM_JOBS} erstellt in {elapsed:.1f}s ({jobs_per_sec:.1f} Jobs/Sek)")
        
        # Test concurrent reads
        print(f"\n[4] Teste {CONCURRENT_READS} gleichzeitige Abrufe...")
        start = time.time()
        tasks = [get_jobs(session, admin_token) for _ in range(CONCURRENT_READS)]
        job_results = await asyncio.gather(*tasks)
        elapsed = time.time() - start
        print(f"  ✅ {results['get_jobs']['success']}/{CONCURRENT_READS} erfolgreich in {elapsed:.1f}s")
        
        if job_results and job_results[0]:
            print(f"  📊 Jobs in DB: {len(job_results[0])} (Seite 1)")
    
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
        min_ms = min(data["times"]) * 1000 if data["times"] else 0
        print(f"{op:20s}: {data['success']:4d}/{total:4d} ({rate:5.1f}%)")
        print(f"                      Ø {avg_ms:6.0f}ms | Min {min_ms:5.0f}ms | Max {max_ms:6.0f}ms")
    
    print("="*60)
    
    # Final stats
    total_ok = sum(d["success"] for d in results.values())
    total_fail = sum(d["failed"] for d in results.values())
    
    if total_fail == 0:
        print("\n🎉 ALLE TESTS ERFOLGREICH!")
    else:
        print(f"\n⚠️  {total_fail} Fehler aufgetreten")
    
    # Capacity estimate
    if results["create_job"]["times"]:
        avg_create = sum(results["create_job"]["times"]) / len(results["create_job"]["times"])
        estimated_per_day = 86400 / avg_create  # Seconds per day / avg time per job
        print(f"\n📈 GESCHÄTZTE KAPAZITÄT:")
        print(f"   - Ø Zeit pro Auftrag: {avg_create*1000:.0f}ms")
        print(f"   - Aufträge/Sekunde: {1/avg_create:.1f}")
        print(f"   - Aufträge/Tag (theoretisch): {estimated_per_day:,.0f}")
    
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())

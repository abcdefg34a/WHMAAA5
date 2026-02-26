#!/usr/bin/env python3
"""
Setup script to create test users for the towing management system
"""

import asyncio
import aiohttp
import json

API_URL = "http://localhost:8000/api"

async def create_test_users():
    """Create the test users needed for testing"""
    
    async with aiohttp.ClientSession() as session:
        
        # 1. Create Admin User
        print("Creating admin user...")
        admin_data = {
            "email": "admin@test.de",
            "password": "Admin123!",
            "name": "Test Administrator",
            "role": "admin"
        }
        
        try:
            async with session.post(f"{API_URL}/auth/register", json=admin_data) as resp:
                if resp.status in [200, 201]:
                    result = await resp.json()
                    print(f"✅ Admin user created successfully")
                else:
                    error = await resp.text()
                    print(f"❌ Admin user creation failed: {resp.status} - {error}")
        except Exception as e:
            print(f"❌ Admin user creation error: {e}")
        
        # 2. Create Authority User
        print("Creating authority user...")
        authority_data = {
            "email": "behoerde@test.de",
            "password": "Behoerde123",
            "name": "Test Behörde",
            "role": "authority",
            "authority_name": "Test Ordnungsamt",
            "department": "Verkehrsüberwachung",
            "dienstnummer": "TEST001"
        }
        
        try:
            async with session.post(f"{API_URL}/auth/register", json=authority_data) as resp:
                if resp.status in [200, 201, 202]:
                    result = await resp.json()
                    print(f"✅ Authority user created successfully")
                else:
                    error = await resp.text()
                    print(f"❌ Authority user creation failed: {resp.status} - {error}")
        except Exception as e:
            print(f"❌ Authority user creation error: {e}")
        
        # 3. Create Towing Service User
        print("Creating towing service user...")
        towing_data = {
            "email": "abschlepp@test.de",
            "password": "Abschlepp123",
            "name": "Test Abschleppdienst",
            "role": "towing_service",
            "company_name": "Test Abschleppdienst GmbH",
            "phone": "+49 30 12345678",
            "address": "Teststraße 123, 10115 Berlin",
            "yard_address": "Hofstraße 456, 10115 Berlin",
            "opening_hours": "Mo-Fr 08:00-18:00, Sa 09:00-14:00",
            "tow_cost": 150.0,
            "daily_cost": 25.0,
            "business_license": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        }
        
        try:
            async with session.post(f"{API_URL}/auth/register", json=towing_data) as resp:
                if resp.status in [200, 201, 202]:
                    result = await resp.json()
                    print(f"✅ Towing service user created successfully")
                else:
                    error = await resp.text()
                    print(f"❌ Towing service user creation failed: {resp.status} - {error}")
        except Exception as e:
            print(f"❌ Towing service user creation error: {e}")
        
        print("\n🎯 Test user setup completed!")
        print("You can now login with:")
        print("- Admin: admin@test.de / Admin123!")
        print("- Authority: behoerde@test.de / Behoerde123")
        print("- Towing Service: abschlepp@test.de / Abschlepp123")

if __name__ == "__main__":
    asyncio.run(create_test_users())
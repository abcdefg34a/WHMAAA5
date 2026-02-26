import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
import sys
sys.path.append(os.path.abspath('backend'))
from server import hash_password
from dotenv import load_dotenv

load_dotenv('backend/.env')

async def main():
    mongo_url = os.environ['MONGO_URL']
    db_name = os.environ['DB_NAME']
    print(f"Connecting to {db_name}...")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    # Admin user
    pwd = hash_password('Admin123!')
    await db.users.update_one(
        {"email": "admin@test.de"},
        {"$set": {"password": pwd}}
    )
    print("Updated admin password.")

    # Authority user
    pwd2 = hash_password('Behoerde123')
    await db.users.update_one(
        {"email": "behoerde@test.de"},
        {"$set": {"password": pwd2}}
    )
    print("Updated behoerde password.")

    # Towing service user
    pwd3 = hash_password('Abschlepp123')
    await db.users.update_one(
        {"email": "abschlepp@test.de"},
        {"$set": {"password": pwd3}}
    )
    print("Updated abschlepp password.")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())

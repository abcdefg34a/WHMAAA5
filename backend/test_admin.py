import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def run():
    client = AsyncIOMotorClient(os.getenv('MONGO_URL'))
    db = client[os.getenv('DB_NAME')]
    user = await db.users.find_one({'email': 'admin@abschleppapp.de'})
    if user:
        print(f"Found user: {user.get('email')}")
        print(f"Password hash: {user.get('password')}")
        print(f"Role: {user.get('role')}")
        print(f"2FA enabled: {user.get('totp_enabled')}")
    else:
        print("Admin user not found.")
        
    client.close()

if __name__ == "__main__":
    asyncio.run(run())

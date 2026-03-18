import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def run():
    client = AsyncIOMotorClient(os.getenv('MONGO_URL'))
    db = client[os.getenv('DB_NAME')]
    
    user = await db.users.find_one({'email': 'admin@test.de'})
    if user:
        print(f"User found. 2FA enabled: {user.get('totp_enabled')}")
        await db.users.update_one(
            {'email': 'admin@test.de'},
            {'$set': {'totp_enabled': False}, '$unset': {'totp_secret': ""}}
        )
        print("Cleared 2FA.")
    else:
        print("User not found.")
        
    client.close()

if __name__ == "__main__":
    asyncio.run(run())

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv('.env')

async def main():
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]

    users = await db.users.find().to_list(length=None)
    for user in users:
        print(f"User: {user.get('email')}")
        print(f"  Role: {user.get('role')}")
        pwd = user.get('password', '')
        print(f"  Password Length: {len(pwd)}")
        print(f"  Password Starts With: {pwd[:4] if pwd else 'None'}")
        
    client.close()

if __name__ == "__main__":
    asyncio.run(main())

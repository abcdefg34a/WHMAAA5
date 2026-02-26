import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
import sys
from dotenv import load_dotenv

load_dotenv('backend/.env')

async def main():
    mongo_url = os.environ['MONGO_URL']
    db_name = os.environ['DB_NAME']
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    print("Dropping old users collection...")
    await db.users.drop()
    print("Done dropping.")
    client.close()

if __name__ == "__main__":
    asyncio.run(main())

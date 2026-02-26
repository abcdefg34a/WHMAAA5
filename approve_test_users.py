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

    print("Approving authority and towing service...")
    await db.users.update_many(
        {"role": {"$in": ["authority", "towing_service"]}},
        {"$set": {"approval_status": "approved"}}
    )
    print("Done approving.")
    client.close()

if __name__ == "__main__":
    asyncio.run(main())

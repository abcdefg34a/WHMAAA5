import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv('.env')

async def main():
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    
    db_names = await client.list_database_names()
    print("Databases in cluster:", db_names)
    
    for db_name in db_names:
        if db_name in ['admin', 'local', 'config']:
            continue
        db = client[db_name]
        try:
            users_count = await db.users.count_documents({})
            print(f"Database '{db_name}' has {users_count} users")
            if users_count > 0:
                print(f"Found non-empty users collection in {db_name}!")
        except Exception as e:
            print(f"Could not read from {db_name}: {e}")
            
    client.close()

if __name__ == "__main__":
    asyncio.run(main())

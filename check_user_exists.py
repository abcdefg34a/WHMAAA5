import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
import sys
sys.path.append(os.path.abspath('backend'))
from dotenv import load_dotenv

load_dotenv('backend/.env')

async def main():
    mongo_url = os.environ['MONGO_URL']
    db_name = os.environ['DB_NAME']
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    user = await db.users.find_one({"email": "admin@test.de"})
    if user:
        print("User EXISITS!")
        print(user)
    else:
        print("USER DOES NOT EXIST!")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())

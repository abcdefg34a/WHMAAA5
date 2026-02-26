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

    user = await db.users.find_one({"email": "behoerde@test.de"})
    if user:
        print("User EXISITS!")
        print("is_main_authority:", user.get("is_main_authority"))
        print("role:", user.get("role"))
        # Print all keys
        for k, v in user.items():
            if k != "password":
                print(f"{k}: {v}")
    else:
        print("USER DOES NOT EXIST!")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())

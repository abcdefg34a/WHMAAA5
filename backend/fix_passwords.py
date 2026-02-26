import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from server import hash_password, verify_password
from dotenv import load_dotenv

load_dotenv('.env')

async def main():
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]

    users = await db.users.find().to_list(length=None)
    updated_count = 0
    
    # Optional: Set a temporary default password for everyone if we don't know the plain texts
    default_password = "Password123!"
    hashed_default = hash_password(default_password)

    for user in users:
        print(f"Checking user: {user.get('email')}")
        # Check if password is valid bcrypt hash
        try:
            # check the hash length and format (bcrypt is 60 chars)
            pwd = user.get('password', '')
            if len(pwd) == 60 and pwd.startswith('$2b$'):
                print(f"  -> User {user.get('email')} already has a bcrypt hash.")
            else:
                raise ValueError("Not a bcrypt hash")
        except ValueError:
            # Not a bcrypt hash, let's update it
            print(f"  -> User {user.get('email')} has invalid hash. Updating to: {default_password}")
            await db.users.update_one(
                {"_id": user["_id"]},
                {"$set": {"password": hashed_default}}
            )
            updated_count += 1
            
    print(f"Updated {updated_count} user passwords.")
    client.close()

if __name__ == "__main__":
    asyncio.run(main())

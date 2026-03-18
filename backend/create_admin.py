import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import bcrypt
from datetime import datetime

load_dotenv()

async def run():
    client = AsyncIOMotorClient(os.getenv('MONGO_URL'))
    db = client[os.getenv('DB_NAME')]
    
    # Check if admin already exists
    existing = await db.users.find_one({'email': 'admin@abschleppapp.de'})
    if existing:
        print("Admin user already exists. Updating missing fields...")
        await db.users.update_one(
            {'_id': existing['_id']},
            {'$set': {
                'created_at': datetime.now().isoformat(),
                'approval_status': 'approved'
            }}
        )
        print("Fields updated.")
    else:
        print("Creating admin user...")
        pwd = bcrypt.hashpw('admin'.encode(), bcrypt.gensalt()).decode()
        await db.users.insert_one({
            'email': 'admin@abschleppapp.de', 
            'password': pwd, 
            'role': 'admin', 
            'name': 'Admin User', 
            'totp_enabled': False,
            'created_at': datetime.now().isoformat(),
            'approval_status': 'approved'
        })
        print('User created')
        
    client.close()

if __name__ == "__main__":
    asyncio.run(run())

import asyncio
import os
import jwt
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv('backend/.env')

async def main():
    # 1. Login to get token
    login_url = "http://localhost:8000/api/auth/login"
    data = {"email": "admin@test.de", "password": "Admin123!"}
    resp = requests.post(login_url, json=data)
    token = resp.json().get('access_token')
    if not token:
        print("Login failed:", resp.text)
        return
        
    print("Got token length:", len(token))
    
    # 2. Decode token
    JWT_SECRET = os.environ.get('JWT_SECRET', 'dev_secret')  # check what env has
    payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    user_id = payload.get("user_id")
    print("Token payload user_id:", user_id)
    
    # 3. Query DB
    mongo_url = os.environ['MONGO_URL']
    db_name = os.environ['DB_NAME']
    print("Connecting to DB:", db_name)
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    user_by_id = await db.users.find_one({"id": user_id})
    print("User in DB by id:", bool(user_by_id))
    if user_by_id:
        print("User id:", user_by_id.get('id'))
    else:
        # try finding by email to see what id it has
        u = await db.users.find_one({"email": "admin@test.de"})
        print("User found by email instead! id is:", u.get('id') if u else None)
        
    client.close()

if __name__ == "__main__":
    asyncio.run(main())

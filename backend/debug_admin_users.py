import requests

def test_admin_users():
    login_url = "http://localhost:8000/api/auth/login"
    data = {
        "email": "admin@test.de",
        "password": "Admin123!"
    }
    
    print("Testing login...")
    response = requests.post(login_url, json=data)
    print("Login Status:", response.status_code)
    print("Login Response:", response.text)
    token = response.json().get('access_token')
    if not token:
        print("No token received, aborting.")
        return
        
    users_url = "http://localhost:8000/api/admin/users"
    headers = {"Authorization": f"Bearer {token}"}
    users_resp = requests.get(users_url, headers=headers)
    
    print(f"\nUsers API Status Code: {users_resp.status_code}")
    if users_resp.status_code != 200:
        print(f"Error Response: {users_resp.text}")
    else:
        users = users_resp.json()
        print(f"Success! Found {len(users)} users.")

if __name__ == "__main__":
    test_admin_users()

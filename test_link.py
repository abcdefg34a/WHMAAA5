import requests

def test_link():
    login_url = "http://localhost:8000/api/auth/login"
    data = {"email": "behoerde@test.de", "password": "Behoerde123"}
    resp = requests.post(login_url, json=data)
    token = resp.json().get('access_token')
    if not token:
        print("Login failed!", resp.text)
        return
        
    link_url = "http://localhost:8000/api/services/link"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"service_code": "ANYHTING"}
    
    res = requests.post(link_url, json=payload, headers=headers)
    print("Link Status:", res.status_code)
    print("Link Response:", res.text)

if __name__ == "__main__":
    test_link()
